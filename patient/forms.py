from django import forms
from django.contrib.auth.models import User
from . import models
import re


class PatientUserForm(forms.ModelForm):
    class Meta:
        model=User
        fields=['first_name','last_name','username','password']
        widgets = {
        'password': forms.PasswordInput()
        }

class PatientForm(forms.ModelForm):
    
    class Meta:
        model=models.Patient
        fields=['age','bloodgroup','aadhaar_number','disease','address','doctorname','mobile','profile_pic']
        widgets = {
            'aadhaar_number': forms.TextInput(attrs={
                'placeholder': 'Enter 12-digit Aadhaar number',
                'maxlength': '12',
                'pattern': '[0-9]{12}',
                'title': 'Please enter a valid 12-digit Aadhaar number'
            })
        }
    
    def clean_aadhaar_number(self):
        aadhaar = self.cleaned_data.get('aadhaar_number')
        if aadhaar:
            # Remove any spaces or special characters
            aadhaar = re.sub(r'\D', '', aadhaar)
            
            # Check if it's exactly 12 digits
            if len(aadhaar) != 12:
                raise forms.ValidationError('Aadhaar number must be exactly 12 digits.')
            
            # Basic Aadhaar validation (simple check)
            if not aadhaar.isdigit():
                raise forms.ValidationError('Aadhaar number must contain only digits.')
                
            # Check if this Aadhaar number already exists (only if not empty)
            if models.Patient.objects.filter(aadhaar_number=aadhaar).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('This Aadhaar number is already registered.')
                
        return aadhaar
