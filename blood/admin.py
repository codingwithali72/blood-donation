from django.contrib import admin
from . import models

# Register your models here.
@admin.register(models.Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['bloodgroup', 'unit', 'unit_in_ml']
    list_filter = ['bloodgroup']
    ordering = ['bloodgroup']

@admin.register(models.BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display = ['bloodgroup', 'unit', 'status', 'date', 'request_by_patient', 'request_by_donor']
    list_filter = ['bloodgroup', 'status', 'date']
    search_fields = ['patient_name', 'bloodgroup']
    ordering = ['-date']
    readonly_fields = ['date']

@admin.register(models.Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'blood_bank_available', 'is_partner', 'contact_phone']
    list_filter = ['city', 'state', 'blood_bank_available', 'is_partner']
    search_fields = ['name', 'city', 'contact_email']
    ordering = ['name']

@admin.register(models.HospitalBloodStock)
class HospitalBloodStockAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'blood_group', 'units_available', 'last_updated']
    list_filter = ['blood_group', 'hospital__city']
    search_fields = ['hospital__name']
    ordering = ['hospital', 'blood_group']
    readonly_fields = ['last_updated']

@admin.register(models.Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['donor', 'certificate_type', 'donation_count', 'issued_date', 'certificate_id']
    list_filter = ['certificate_type', 'issued_date']
    search_fields = ['donor__user__first_name', 'donor__user__last_name', 'certificate_id']
    ordering = ['-issued_date']
    readonly_fields = ['issued_date', 'certificate_id']

@admin.register(models.Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'is_active', 'contact_email']
    list_filter = ['city', 'state', 'is_active']
    search_fields = ['name', 'contact_email']
    ordering = ['name']

@admin.register(models.BloodCamp)
class BloodCampAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'city', 'status', 'target_donors', 'actual_donors']
    list_filter = ['status', 'start_date', 'city']
    search_fields = ['name', 'organizer']
    ordering = ['-start_date']
    readonly_fields = ['created_date']

@admin.register(models.CampRegistration)
class CampRegistrationAdmin(admin.ModelAdmin):
    list_display = ['camp', 'donor', 'registered_date', 'attended', 'donated']
    list_filter = ['attended', 'donated', 'registered_date']
    search_fields = ['camp__name', 'donor__user__first_name', 'donor__user__last_name']
    ordering = ['-registered_date']
    readonly_fields = ['registered_date']
