from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.db.models import Sum,Q
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required,user_passes_test
from django.conf import settings
from datetime import date, timedelta
from django.core.mail import send_mail
from django.contrib.auth.models import User
from donor import models as dmodels
from patient import models as pmodels
from donor import forms as dforms
from patient import forms as pforms
from django.template.loader import render_to_string
from django.contrib import messages
from io import BytesIO

# Optional imports for PDF generation
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from django.conf import settings
    import os
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Terms and Privacy Policy Views
def terms_view(request):
    """View function for Terms & Conditions page"""
    return render(request, 'blood/terms.html')

def privacy_view(request):
    """View function for Privacy Policy page"""
    return render(request, 'blood/privacy.html')

def home_view(request):
    x=models.Stock.objects.all()
    if len(x)==0:
        blood1=models.Stock()
        blood1.bloodgroup="A+"
        blood1.save()

        blood2=models.Stock()
        blood2.bloodgroup="A-"
        blood2.save()

        blood3=models.Stock()
        blood3.bloodgroup="B+"
        blood3.save()        

        blood4=models.Stock()
        blood4.bloodgroup="B-"
        blood4.save()

        blood5=models.Stock()
        blood5.bloodgroup="AB+"
        blood5.save()

        blood6=models.Stock()
        blood6.bloodgroup="AB-"
        blood6.save()

        blood7=models.Stock()
        blood7.bloodgroup="O+"
        blood7.save()

        blood8=models.Stock()
        blood8.bloodgroup="O-"
        blood8.save()

    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')  
    return render(request,'blood/index.html')

def loginregister_view(request):
    """Unified login and register page with tab switching"""
    context = {
        'page_title': 'Login / Register',
        'page_description': 'Access your account or create a new one to join our life-saving community'
    }
    return render(request, 'blood/loginregister.html', context)

def is_donor(user):
    return user.groups.filter(name='DONOR').exists()

def is_patient(user):
    return user.groups.filter(name='PATIENT').exists()


def afterlogin_view(request):
    if is_donor(request.user):      
        return redirect('donor/donor-dashboard')
                
    elif is_patient(request.user):
        return redirect('patient/patient-dashboard')
    else:
        return redirect('admin-dashboard')

@login_required(login_url='adminlogin')
def admin_dashboard_view(request):
    totalunit=models.Stock.objects.aggregate(Sum('unit'))
    
    # Get recent certificates for notifications
    recent_certificates = models.Certificate.objects.filter(
        issued_date__gte=date.today() - timedelta(days=7)
    ).order_by('-issued_date')[:5]
    
    dict={
        'A1':models.Stock.objects.get(bloodgroup="A+"),
        'A2':models.Stock.objects.get(bloodgroup="A-"),
        'B1':models.Stock.objects.get(bloodgroup="B+"),
        'B2':models.Stock.objects.get(bloodgroup="B-"),
        'AB1':models.Stock.objects.get(bloodgroup="AB+"),
        'AB2':models.Stock.objects.get(bloodgroup="AB-"),
        'O1':models.Stock.objects.get(bloodgroup="O+"),
        'O2':models.Stock.objects.get(bloodgroup="O-"),
        'totaldonors':dmodels.Donor.objects.all().count(),
        'totalbloodunit':totalunit['unit__sum'],
        'totalrequest':models.BloodRequest.objects.all().count(),
        'totalapprovedrequest':models.BloodRequest.objects.all().filter(status='Approved').count(),
        'recent_certificates': recent_certificates,
        'total_certificates': models.Certificate.objects.count(),
        'blood_camps_count': models.BloodCamp.objects.filter(status='PLANNED').count(),
        'sponsors_count': models.Sponsor.objects.filter(is_active=True).count(),
    }
    return render(request,'blood/admin_dashboard.html',context=dict)

@login_required(login_url='adminlogin')
def admin_blood_view(request):
    dict={
        'bloodForm':forms.BloodForm(),
        'A1':models.Stock.objects.get(bloodgroup="A+"),
        'A2':models.Stock.objects.get(bloodgroup="A-"),
        'B1':models.Stock.objects.get(bloodgroup="B+"),
        'B2':models.Stock.objects.get(bloodgroup="B-"),
        'AB1':models.Stock.objects.get(bloodgroup="AB+"),
        'AB2':models.Stock.objects.get(bloodgroup="AB-"),
        'O1':models.Stock.objects.get(bloodgroup="O+"),
        'O2':models.Stock.objects.get(bloodgroup="O-"),
    }
    if request.method=='POST':
        bloodForm=forms.BloodForm(request.POST)
        if bloodForm.is_valid() :        
            bloodgroup=bloodForm.cleaned_data['bloodgroup']
            stock=models.Stock.objects.get(bloodgroup=bloodgroup)
            stock.unit=bloodForm.cleaned_data['unit']
            stock.save()
        return HttpResponseRedirect('admin-blood')
    return render(request,'blood/admin_blood.html',context=dict)


@login_required(login_url='adminlogin')
def admin_donor_view(request):
    donors=dmodels.Donor.objects.all()
    return render(request,'blood/admin_donor.html',{'donors':donors})

@login_required(login_url='adminlogin')
def update_donor_view(request,pk):
    donor=dmodels.Donor.objects.get(id=pk)
    user=dmodels.User.objects.get(id=donor.user_id)
    userForm=dforms.DonorUserForm(instance=user)
    donorForm=dforms.DonorForm(request.FILES,instance=donor)
    mydict={'userForm':userForm,'donorForm':donorForm}
    if request.method=='POST':
        userForm=dforms.DonorUserForm(request.POST,instance=user)
        donorForm=dforms.DonorForm(request.POST,request.FILES,instance=donor)
        if userForm.is_valid() and donorForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            donor=donorForm.save(commit=False)
            donor.user=user
            donor.bloodgroup=donorForm.cleaned_data['bloodgroup']
            if 'aadhaar_number' in donorForm.cleaned_data:
                donor.aadhaar_number=donorForm.cleaned_data['aadhaar_number']
            donor.save()
            return redirect('admin-donor')
    return render(request,'blood/update_donor.html',context=mydict)


@login_required(login_url='adminlogin')
def delete_donor_view(request,pk):
    donor=dmodels.Donor.objects.get(id=pk)
    user=User.objects.get(id=donor.user_id)
    user.delete()
    donor.delete()
    return HttpResponseRedirect('/admin-donor')

@login_required(login_url='adminlogin')
def admin_patient_view(request):
    patients=pmodels.Patient.objects.all()
    return render(request,'blood/admin_patient.html',{'patients':patients})


@login_required(login_url='adminlogin')
def update_patient_view(request,pk):
    patient=pmodels.Patient.objects.get(id=pk)
    user=pmodels.User.objects.get(id=patient.user_id)
    userForm=pforms.PatientUserForm(instance=user)
    patientForm=pforms.PatientForm(request.FILES,instance=patient)
    mydict={'userForm':userForm,'patientForm':patientForm}
    if request.method=='POST':
        userForm=pforms.PatientUserForm(request.POST,instance=user)
        patientForm=pforms.PatientForm(request.POST,request.FILES,instance=patient)
        if userForm.is_valid() and patientForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            patient=patientForm.save(commit=False)
            patient.user=user
            patient.bloodgroup=patientForm.cleaned_data['bloodgroup']
            if 'aadhaar_number' in patientForm.cleaned_data:
                patient.aadhaar_number=patientForm.cleaned_data['aadhaar_number']
            patient.save()
            return redirect('admin-patient')
    return render(request,'blood/update_patient.html',context=mydict)


@login_required(login_url='adminlogin')
def delete_patient_view(request,pk):
    patient=pmodels.Patient.objects.get(id=pk)
    user=User.objects.get(id=patient.user_id)
    user.delete()
    patient.delete()
    return HttpResponseRedirect('/admin-patient')

@login_required(login_url='adminlogin')
def admin_request_view(request):
    requests=models.BloodRequest.objects.all().filter(status='Pending')
    return render(request,'blood/admin_request.html',{'requests':requests})

@login_required(login_url='adminlogin')
def admin_request_history_view(request):
    requests=models.BloodRequest.objects.all().exclude(status='Pending')
    return render(request,'blood/admin_request_history.html',{'requests':requests})

@login_required(login_url='adminlogin')
def admin_donation_view(request):
    donations=dmodels.BloodDonate.objects.all()
    return render(request,'blood/admin_donation.html',{'donations':donations})

@login_required(login_url='adminlogin')
def update_approve_status_view(request,pk):
    req=models.BloodRequest.objects.get(id=pk)
    message=None
    bloodgroup=req.bloodgroup
    unit=req.unit  # Now in bags
    stock=models.Stock.objects.get(bloodgroup=bloodgroup)
    if stock.unit >= unit:
        stock.unit=stock.unit-unit
        stock.save()
        req.status="Approved"
        messages.success(request, f'Blood request approved! {unit} bags of {bloodgroup} blood allocated.')
    else:
        message="Stock Does Not Have Enough Blood To Approve This Request, Only "+str(stock.unit)+" Bags Available"
    req.save()

    requests=models.BloodRequest.objects.all().filter(status='Pending')
    return render(request,'blood/admin_request.html',{'requests':requests,'message':message})

@login_required(login_url='adminlogin')
def update_reject_status_view(request,pk):
    req=models.BloodRequest.objects.get(id=pk)
    req.status="Rejected"
    req.save()
    return HttpResponseRedirect('/admin-request')

@login_required(login_url='adminlogin')
@login_required(login_url='adminlogin')
def approve_donation_view(request,pk):
    donation=dmodels.BloodDonate.objects.get(id=pk)
    donation_blood_group=donation.bloodgroup
    donation_blood_unit=donation.unit  # Now in bags

    stock=models.Stock.objects.get(bloodgroup=donation_blood_group)
    stock.unit=stock.unit+donation_blood_unit
    stock.save()

    donation.status='Approved'
    donation.save()
    
    # Check for new certificates and show detailed feedback
    try:
        new_certificates = check_and_award_certificates(donation.donor)
        
        if new_certificates:
            cert_names = [cert.replace("_", " ").title() for cert in new_certificates]
            messages.success(request, f'Donation approved! 🎉 {donation.donor.get_name} earned new certificates: {", ".join(cert_names)}')
        else:
            # Check current donation count for feedback
            donation_count = dmodels.BloodDonate.objects.filter(
                donor=donation.donor, status='Approved'
            ).count()
            messages.success(request, f'Donation approved! Total donations for {donation.donor.get_name}: {donation_count}')
            
    except Exception as e:
        # Log the error but don't fail the approval  
        messages.success(request, 'Donation approved successfully!')
    
    return HttpResponseRedirect('/admin-donation')


@login_required(login_url='adminlogin')
def reject_donation_view(request,pk):
    donation=dmodels.BloodDonate.objects.get(id=pk)
    donation.status='Rejected'
    donation.save()
    return HttpResponseRedirect('/admin-donation')

# Certificate and Gamification Views
def check_and_award_certificates(donor):
    """Check if donor qualifies for any certificates and award them"""
    # Count approved donations
    approved_donations = dmodels.BloodDonate.objects.filter(
        donor=donor, status='Approved'
    ).count()
    
    certificates_to_award = []
    
    # Define certificate thresholds
    if approved_donations == 1 and not models.Certificate.objects.filter(
        donor=donor, certificate_type='FIRST_DONATION'
    ).exists():
        certificates_to_award.append('FIRST_DONATION')
    
    if approved_donations >= 5 and not models.Certificate.objects.filter(
        donor=donor, certificate_type='REGULAR_DONOR'
    ).exists():
        certificates_to_award.append('REGULAR_DONOR')
    
    if approved_donations >= 10 and not models.Certificate.objects.filter(
        donor=donor, certificate_type='HERO_DONOR'
    ).exists():
        certificates_to_award.append('HERO_DONOR')
    
    if approved_donations >= 20 and not models.Certificate.objects.filter(
        donor=donor, certificate_type='LIFE_SAVER'
    ).exists():
        certificates_to_award.append('LIFE_SAVER')
    
    if approved_donations >= 50 and not models.Certificate.objects.filter(
        donor=donor, certificate_type='BLOOD_CHAMPION'
    ).exists():
        certificates_to_award.append('BLOOD_CHAMPION')
    
    # Award certificates
    for cert_type in certificates_to_award:
        models.Certificate.objects.create(
            donor=donor,
            certificate_type=cert_type,
            donation_count=approved_donations
        )
    
    return certificates_to_award

def draw_certificate_background(canv, doc):
    """Custom background drawer for certificate PDF"""
    width, height = A4
    
    # Path to background pattern
    pattern_path = os.path.join(settings.STATICFILES_DIRS[0], 'images', 'certificates', 'pattern.jpg')
    
    # Check if background image exists
    if os.path.exists(pattern_path):
        try:
            canv.drawImage(pattern_path, 0, 0, width=width, height=height, mask='auto')
        except Exception:
            # Fallback to gradient background if image fails
            canv.setFillColor(colors.HexColor("#fef2f2"))
            canv.rect(0, 0, width, height, fill=1)
    else:
        # Fallback gradient background
        canv.setFillColor(colors.HexColor("#fef2f2"))
        canv.rect(0, 0, width, height, fill=1)

@login_required(login_url='adminlogin')
def approve_donation_view_enhanced(request, pk):
    """Enhanced donation approval with certificate checking"""
    donation = dmodels.BloodDonate.objects.get(id=pk)
    donation_blood_group = donation.bloodgroup
    donation_blood_unit = donation.unit

    stock = models.Stock.objects.get(bloodgroup=donation_blood_group)
    stock.unit = stock.unit + donation_blood_unit
    stock.save()

    donation.status = 'Approved'
    donation.save()
    
    # Check for new certificates
    new_certificates = check_and_award_certificates(donation.donor)
    
    if new_certificates:
        messages.success(request, f'Donation approved! {donation.donor.get_name} earned new certificates: {", ".join([cert.replace("_", " ").title() for cert in new_certificates])}')
    else:
        messages.success(request, 'Donation approved successfully!')
    
    return HttpResponseRedirect('/admin-donation')

@login_required
def donor_certificates_view(request):
    """View for donors to see their certificates"""
    if not is_donor(request.user):
        return redirect('/')
    
    try:
        donor = dmodels.Donor.objects.get(user_id=request.user.id)
        certificates = models.Certificate.objects.filter(donor=donor).order_by('-issued_date')
        
        # Get donation count
        donation_count = dmodels.BloodDonate.objects.filter(
            donor=donor, status='Approved'
        ).count()
        
        # Calculate progress to next milestone
        next_milestone_info = None
        progress_percentage = 0
        
        if donation_count < 5:
            remaining = 5 - donation_count
            next_milestone_info = f"You need {remaining} more donations to become a Regular Donor!"
            progress_percentage = (donation_count / 5) * 100
        elif donation_count < 10:
            remaining = 10 - donation_count
            next_milestone_info = f"You need {remaining} more donations to become a Hero Donor!"
            progress_percentage = ((donation_count - 5) / 5) * 100
        elif donation_count < 20:
            remaining = 20 - donation_count
            next_milestone_info = f"You need {remaining} more donations to become a Life Saver!"
            progress_percentage = ((donation_count - 10) / 10) * 100
        elif donation_count < 50:
            remaining = 50 - donation_count
            next_milestone_info = f"You need {remaining} more donations to become a Blood Champion!"
            progress_percentage = ((donation_count - 20) / 30) * 100
        
        # Calculate lives potentially saved (approximate: 1 donation can save 3 lives)
        lives_saved = donation_count * 3
        
        # Debug: Check for potential certificates
        potential_certificates = []
        if donation_count >= 1 and not certificates.filter(certificate_type='FIRST_DONATION').exists():
            potential_certificates.append('First Donation')
        if donation_count >= 5 and not certificates.filter(certificate_type='REGULAR_DONOR').exists():
            potential_certificates.append('Regular Donor')
        if donation_count >= 10 and not certificates.filter(certificate_type='HERO_DONOR').exists():
            potential_certificates.append('Hero Donor')
        if donation_count >= 20 and not certificates.filter(certificate_type='LIFE_SAVER').exists():
            potential_certificates.append('Life Saver')
        if donation_count >= 50 and not certificates.filter(certificate_type='BLOOD_CHAMPION').exists():
            potential_certificates.append('Blood Champion')
        
        # Automatically award missing certificates
        if potential_certificates:
            new_certificates = check_and_award_certificates(donor)
            if new_certificates:
                messages.success(request, f'Congratulations! You earned new certificates: {", ".join([cert.replace("_", " ").title() for cert in new_certificates])}')
                # Refresh certificates after awarding
                certificates = models.Certificate.objects.filter(donor=donor).order_by('-issued_date')
        
        context = {
            'certificates': certificates,
            'donation_count': donation_count,
            'lives_saved': lives_saved,
            'next_milestone_info': next_milestone_info,
            'progress_percentage': progress_percentage,
            'donor': donor,
            'potential_certificates': potential_certificates,
        }
        return render(request, 'donor/certificates.html', context)
        
    except dmodels.Donor.DoesNotExist:
        messages.error(request, 'Donor profile not found.')
        return redirect('/')

@login_required
def download_certificate_view(request, certificate_id):
    """Generate and download certificate PDF with improved design"""
    try:
        certificate = models.Certificate.objects.get(certificate_id=certificate_id)
        
        # Check if user owns this certificate
        if not (is_donor(request.user) and certificate.donor.user == request.user):
            messages.error(request, 'You are not authorized to download this certificate.')
            return redirect('/')
        
        if not REPORTLAB_AVAILABLE:
            messages.error(request, 'PDF generation is not available. Please contact admin.')
            return redirect('/donor/certificates')
        
        # Create PDF response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="certificate_{certificate_id}.pdf"'
        
        # Create PDF content
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # Custom styles based on your cer.py design
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'title',
            parent=styles['Title'],
            alignment=TA_CENTER,
            fontSize=34,
            textColor=colors.HexColor("#002366"),  # Navy Blue
            spaceAfter=30
        )
        
        name_style = ParagraphStyle(
            'name',
            parent=styles['Title'],
            alignment=TA_CENTER,
            fontSize=26,
            textColor=colors.HexColor("#B22222"),  # Blood Red
            spaceAfter=25
        )
        
        subtitle_style = ParagraphStyle(
            'subtitle',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=16,
            textColor=colors.black,
            spaceAfter=15
        )
        
        footer_style = ParagraphStyle(
            'footer',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=12,
            textColor=colors.HexColor("#072204"),
            spaceAfter=10
        )
        
        certificate_info_style = ParagraphStyle(
            'certificate_info',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=8,
            textColor=colors.HexColor("#5E4E1B"),
            spaceAfter=10
        )
        
        # Certificate content
        elements = []
        elements.append(Spacer(1, 100))
        elements.append(Paragraph("BLOOD DONATION", title_style))
        elements.append(Paragraph("CERTIFICATE", title_style))
        elements.append(Spacer(1, 40))
        
        elements.append(Paragraph("This is to certify that", subtitle_style))
        elements.append(Paragraph(f"<b>{certificate.donor.get_name}</b>", name_style))
        elements.append(Paragraph("has been recognized as a", subtitle_style))
        elements.append(Paragraph(f"<b>{certificate.get_certificate_type_display()}</b>", subtitle_style))
        elements.append(Paragraph(f"for <b>{certificate.donation_count} successful blood donation{'s' if certificate.donation_count > 1 else ''}</b>", subtitle_style))
        
        elements.append(Spacer(1, 60))
        elements.append(Paragraph(f"Certificate ID: {certificate.certificate_id}", certificate_info_style))
        elements.append(Paragraph(f"Issued Date: {certificate.issued_date.strftime('%B %d, %Y')}", certificate_info_style))
        
        elements.append(Spacer(1, 80))
        elements.append(Paragraph("<b>Thank you for saving lives through blood donation!</b>", subtitle_style))
        
        # Build PDF with custom background
        doc.build(elements, onFirstPage=draw_certificate_background, onLaterPages=draw_certificate_background)
        
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
        
    except models.Certificate.DoesNotExist:
        messages.error(request, 'Certificate not found.')
        return redirect('/')
    except Exception as e:
        messages.error(request, f'Error generating certificate: {str(e)}')
        return redirect('/donor/certificates')

# Blood Camp Views
@login_required(login_url='adminlogin')
def admin_blood_camps_view(request):
    """Admin view for managing blood camps"""
    camps = models.BloodCamp.objects.all().order_by('-start_date')
    return render(request, 'blood/admin_blood_camps.html', {'camps': camps})

@login_required(login_url='adminlogin')
def add_blood_camp_view(request):
    """Add new blood camp"""
    if request.method == 'POST':
        form = forms.BloodCampForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Blood camp created successfully!')
            return redirect('admin-blood-camps')
    else:
        form = forms.BloodCampForm()
    
    return render(request, 'blood/add_blood_camp.html', {'form': form})

def blood_camps_list_view(request):
    """Public view for upcoming blood camps - Coming Soon page"""
    # Since we're showing a "Coming Soon" page, we don't need actual camps
    # upcoming_camps = models.BloodCamp.objects.filter(
    #     status='PLANNED',
    #     start_date__gte=date.today()
    # ).order_by('start_date')
    
    context = {'camps': []}  # Empty list for coming soon page
    return render(request, 'blood/blood_camps.html', context)

@login_required
def register_for_camp_view(request, camp_id):
    """Register donor for blood camp"""
    if not is_donor(request.user):
        messages.error(request, 'Only donors can register for blood camps.')
        return redirect('/')
    
    try:
        camp = models.BloodCamp.objects.get(id=camp_id)
        donor = dmodels.Donor.objects.get(user_id=request.user.id)
        
        # Check if already registered
        if models.CampRegistration.objects.filter(camp=camp, donor=donor).exists():
            messages.warning(request, 'You are already registered for this camp.')
        else:
            models.CampRegistration.objects.create(camp=camp, donor=donor)
            camp.registered_donors += 1
            camp.save()
            messages.success(request, 'Successfully registered for the blood camp!')
        
    except (models.BloodCamp.DoesNotExist, dmodels.Donor.DoesNotExist):
        messages.error(request, 'Invalid camp or donor.')
    
    return redirect('blood-camps')

# Sponsor and Hospital Views
@login_required(login_url='adminlogin')
def admin_sponsors_view(request):
    """Admin view for managing sponsors"""
    sponsors = models.Sponsor.objects.all()
    return render(request, 'blood/admin_sponsors.html', {'sponsors': sponsors})

@login_required(login_url='adminlogin')
def admin_hospitals_view(request):
    """Admin view for managing hospitals"""
    hospitals = models.Hospital.objects.all()
    return render(request, 'blood/admin_hospitals.html', {'hospitals': hospitals})

def sponsors_list_view(request):
    """Public view for sponsors"""
    sponsors = models.Sponsor.objects.filter(is_active=True)
    
    # If user is logged in, try to filter by location
    user_city = None
    if request.user.is_authenticated:
        if is_donor(request.user):
            try:
                donor = dmodels.Donor.objects.get(user=request.user)
                # Extract city from address (simple approach)
                user_city = donor.address.split(',')[-1].strip() if donor.address else None
            except dmodels.Donor.DoesNotExist:
                pass
        elif is_patient(request.user):
            try:
                patient = pmodels.Patient.objects.get(user=request.user)
                user_city = patient.address.split(',')[-1].strip() if patient.address else None
            except pmodels.Patient.DoesNotExist:
                pass
    
    # Filter sponsors by city if available
    if user_city:
        local_sponsors = sponsors.filter(city__icontains=user_city)
        other_sponsors = sponsors.exclude(city__icontains=user_city)
    else:
        local_sponsors = []
        other_sponsors = sponsors
    
    context = {
        'local_sponsors': local_sponsors,
        'other_sponsors': other_sponsors,
        'user_city': user_city,
    }
    return render(request, 'blood/sponsors.html', context)

def hospitals_list_view(request):
    """Public view for hospitals"""
    hospitals = models.Hospital.objects.filter(is_partner=True)
    
    # Similar location-based filtering as sponsors
    user_city = None
    if request.user.is_authenticated:
        if is_donor(request.user):
            try:
                donor = dmodels.Donor.objects.get(user=request.user)
                user_city = donor.address.split(',')[-1].strip() if donor.address else None
            except dmodels.Donor.DoesNotExist:
                pass
        elif is_patient(request.user):
            try:
                patient = pmodels.Patient.objects.get(user=request.user)
                user_city = patient.address.split(',')[-1].strip() if patient.address else None
            except pmodels.Patient.DoesNotExist:
                pass
    
    if user_city:
        local_hospitals = hospitals.filter(city__icontains=user_city)
        other_hospitals = hospitals.exclude(city__icontains=user_city)
    else:
        local_hospitals = []
        other_hospitals = hospitals
    
    context = {
        'local_hospitals': local_hospitals,
        'other_hospitals': other_hospitals,
        'user_city': user_city,
    }
    return render(request, 'blood/hospitals.html', context)