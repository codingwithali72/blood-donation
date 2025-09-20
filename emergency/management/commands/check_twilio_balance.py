from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check Twilio account balance and SMS credits remaining'

    def add_arguments(self, parser):
        parser.add_argument(
            '--alert-threshold',
            type=float,
            default=5.0,
            help='Send alert when balance falls below this amount (default: $5.00)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed usage statistics'
        )

    def handle(self, *args, **options):
        try:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            # Get account information
            account = client.api.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
            balance = client.balance.fetch()
            
            current_balance = float(balance.balance)
            sms_cost_per_message = 0.0065  # USD per SMS to India
            approximate_sms_credits = current_balance / sms_cost_per_message
            
            self.stdout.write("=" * 60)
            self.stdout.write(f"📋 TWILIO BALANCE CHECK - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.stdout.write("=" * 60)
            self.stdout.write(f"💰 Current Balance: ${current_balance:.4f} {balance.currency}")
            self.stdout.write(f"📱 Approximate SMS Credits: ~{approximate_sms_credits:.0f} messages")
            self.stdout.write(f"📊 Account Status: {account.status} ({account.type})")
            
            # Check if balance is low
            alert_threshold = options['alert_threshold']
            if current_balance < alert_threshold:
                self.stdout.write(
                    self.style.WARNING(f"\n⚠️  LOW BALANCE ALERT: ${current_balance:.4f} is below threshold ${alert_threshold:.2f}")
                )
                self.stdout.write(
                    self.style.WARNING(f"📱 Only ~{approximate_sms_credits:.0f} SMS messages remaining!")
                )
                
                if account.type.lower() == 'trial':
                    self.stdout.write(
                        self.style.NOTICE("\n🆓 Consider upgrading from trial account for:")
                    )
                    self.stdout.write("• Remove 'trial account' prefix from SMS messages")
                    self.stdout.write("• Send to any phone number (not just verified)")
                    self.stdout.write("• Access to more Twilio features")
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"\n✅ Balance is healthy (${current_balance:.4f} >= ${alert_threshold:.2f})")
                )
            
            # Show detailed usage if requested
            if options['verbose']:
                from datetime import datetime, timedelta
                
                self.stdout.write(f"\n📊 USAGE STATISTICS (Last 7 Days)")
                self.stdout.write("-" * 40)
                
                seven_days_ago = datetime.now() - timedelta(days=7)
                
                try:
                    usage_records = client.usage.records.list(
                        category='sms',
                        start_date=seven_days_ago.date(),
                        end_date=datetime.now().date()
                    )
                    
                    total_sms = 0
                    total_cost = 0.0
                    
                    for record in usage_records:
                        daily_count = int(record.count)
                        daily_cost = float(record.price)
                        total_sms += daily_count
                        total_cost += daily_cost
                        
                        if daily_count > 0:  # Only show days with activity
                            self.stdout.write(f"📅 {record.start_date}: {daily_count} SMS, ${daily_cost:.4f}")
                    
                    if total_sms > 0:
                        self.stdout.write(f"\n📈 Week Total: {total_sms} SMS messages")
                        self.stdout.write(f"💳 Week Cost: ${total_cost:.4f}")
                        avg_per_day = total_sms / 7
                        self.stdout.write(f"📊 Average: {avg_per_day:.1f} SMS/day")
                    else:
                        self.stdout.write("📊 No SMS usage in the last 7 days")
                        
                except Exception as e:
                    self.stdout.write(f"⚠️  Could not fetch usage statistics: {str(e)}")
            
            # Show phone numbers
            try:
                phone_numbers = client.incoming_phone_numbers.list(limit=5)
                if phone_numbers:
                    self.stdout.write(f"\n📞 TWILIO PHONE NUMBERS")
                    self.stdout.write("-" * 25)
                    for number in phone_numbers:
                        self.stdout.write(f"📱 {number.phone_number}")
            except Exception as e:
                self.stdout.write(f"⚠️  Could not fetch phone numbers: {str(e)}")
            
            self.stdout.write("=" * 60)
            
            # Create balance check record for monitoring
            try:
                from emergency.models import EmergencyAnalytics
                from django.db import transaction
                
                with transaction.atomic():
                    analytics, created = EmergencyAnalytics.objects.get_or_create(
                        date=timezone.now().date(),
                        blood_group='',  # Use empty for system stats
                        city='TWILIO_BALANCE',
                        defaults={
                            'balance_amount': current_balance,
                            'sms_credits_remaining': int(approximate_sms_credits),
                            'notes': f"Balance check at {timezone.now().isoformat()}"
                        }
                    )
                    
                    if not created:
                        analytics.balance_amount = current_balance
                        analytics.sms_credits_remaining = int(approximate_sms_credits)
                        analytics.notes = f"Balance updated at {timezone.now().isoformat()}"
                        analytics.save()
                        
            except Exception as e:
                logger.warning(f"Could not save balance check record: {e}")
            
            return f"Balance check completed: ${current_balance:.4f}, ~{approximate_sms_credits:.0f} SMS credits"
            
        except TwilioException as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Twilio API Error: {str(e)}")
            )
            raise
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error checking balance: {str(e)}")
            )
            raise