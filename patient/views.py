from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.db.models import Sum,Q
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required,user_passes_test
from django.conf import settings
from datetime import date, timedelta
from django.core.mail import send_mail
from django.contrib.auth.models import User
from blood import forms as bforms
from blood import models as bmodels
from blood.services import BloodRequestService
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.conf import settings


def patient_signup_view(request):
    userForm=forms.PatientUserForm()
    patientForm=forms.PatientForm()
    mydict={'userForm':userForm,'patientForm':patientForm}
    if request.method=='POST':
        userForm=forms.PatientUserForm(request.POST)
        patientForm=forms.PatientForm(request.POST,request.FILES)
        if userForm.is_valid() and patientForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            patient=patientForm.save(commit=False)
            patient.user=user
            patient.bloodgroup=patientForm.cleaned_data['bloodgroup']
            patient.aadhaar_number=patientForm.cleaned_data['aadhaar_number']
            patient.save()
            my_patient_group = Group.objects.get_or_create(name='PATIENT')
            my_patient_group[0].user_set.add(user)
            
            # Auto-login the user and redirect to dashboard
            login(request, user)
            return HttpResponseRedirect('/patient/patient-dashboard')
        return HttpResponseRedirect('patientlogin')
    return render(request,'patient/patientsignup.html',context=mydict)

def patient_dashboard_view(request):
    patient= models.Patient.objects.get(user_id=request.user.id)
    dict={
        'requestpending': bmodels.BloodRequest.objects.all().filter(request_by_patient=patient).filter(status='Pending').count(),
        'requestapproved': bmodels.BloodRequest.objects.all().filter(request_by_patient=patient).filter(status='Approved').count(),
        'requestmade': bmodels.BloodRequest.objects.all().filter(request_by_patient=patient).count(),
        'requestrejected': bmodels.BloodRequest.objects.all().filter(request_by_patient=patient).filter(status='Rejected').count(),

    }
   
    return render(request,'patient/patient_dashboard.html',context=dict)

def make_request_view(request):
    # Check if simplified request is preferred (can be a query parameter)
    use_simplified = request.GET.get('simplified', 'true').lower() == 'true'
    
    if use_simplified:
        request_form = bforms.SimplifiedRequestForm()
        template = 'patient/makerequest_simplified.html'
    else:
        request_form = bforms.RequestForm()
        template = 'patient/makerequest.html'
    
    if request.method == 'POST':
        if use_simplified:
            request_form = bforms.SimplifiedRequestForm(request.POST)
        else:
            request_form = bforms.RequestForm(request.POST)
            
        if request_form.is_valid():
            blood_request = request_form.save(commit=False)
            blood_request.bloodgroup = request_form.cleaned_data['bloodgroup']
            patient = models.Patient.objects.get(user_id=request.user.id)
            blood_request.request_by_patient = patient
            
            # For traditional requests, ensure required fields are present
            if not use_simplified:
                blood_request.patient_name = request_form.cleaned_data.get('patient_name')
                blood_request.patient_age = request_form.cleaned_data.get('patient_age')
                blood_request.reason = request_form.cleaned_data.get('reason')
            else:
                # For simplified requests, use patient's info as defaults
                blood_request.patient_name = patient.user.get_full_name() or patient.user.username
                blood_request.patient_age = patient.age if hasattr(patient, 'age') else None
                blood_request.reason = 'Emergency blood requirement'
            
            blood_request.save()
            
            # Process the request for nearby hospitals (simplified flow)
            if use_simplified and blood_request.latitude and blood_request.longitude:
                try:
                    nearby_hospitals = BloodRequestService.process_blood_request(blood_request)
                    if nearby_hospitals:
                        messages.success(request, f'Blood request submitted! Found {len(nearby_hospitals)} nearby hospitals with {blood_request.bloodgroup} blood. Check your email and SMS for hospital details.')
                    else:
                        messages.warning(request, f'Blood request submitted, but no nearby hospitals found with {blood_request.bloodgroup} blood. We will notify you if blood becomes available.')
                except Exception as e:
                    messages.warning(request, 'Blood request submitted. Notification service temporarily unavailable.')
            else:
                messages.success(request, 'Blood request submitted successfully!')
            
            return HttpResponseRedirect('my-request')
    
    context = {
        'request_form': request_form,
        'use_simplified': use_simplified,
        'blood_bag_ml_ratio': getattr(settings, 'BLOOD_BAG_TO_ML_RATIO', 350)
    }
    return render(request, template, context)

def my_request_view(request):
    patient= models.Patient.objects.get(user_id=request.user.id)
    blood_request=bmodels.BloodRequest.objects.all().filter(request_by_patient=patient)
    return render(request,'patient/my_request.html',{'blood_request':blood_request})
