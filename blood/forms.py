from django import forms
from . import models


class BloodForm(forms.ModelForm):
    class Meta:
        model=models.Stock
        fields=['bloodgroup','unit']

class RequestForm(forms.ModelForm):
    class Meta:
        model=models.BloodRequest
        fields=['patient_name','patient_age','reason','bloodgroup','unit']

class SimplifiedRequestForm(forms.ModelForm):
    BLOOD_GROUP_CHOICES = [
        ('', 'Select Blood Group'),
        ('O+', 'O+ (O Positive)'),
        ('O-', 'O- (O Negative)'),
        ('A+', 'A+ (A Positive)'),
        ('A-', 'A- (A Negative)'),
        ('B+', 'B+ (B Positive)'),
        ('B-', 'B- (B Negative)'),
        ('AB+', 'AB+ (AB Positive)'),
        ('AB-', 'AB- (AB Negative)'),
    ]
    
    bloodgroup = forms.ChoiceField(
        choices=BLOOD_GROUP_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        })
    )
    
    unit = forms.IntegerField(
        min_value=1,
        max_value=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter number of bags needed',
            'required': True
        }),
        help_text='Number of blood bags required (1 bag = 350ml)'
    )
    
    # Hidden fields for location (will be populated by JavaScript)
    latitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)
    longitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)
    location_address = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = models.BloodRequest
        fields = ['bloodgroup', 'unit', 'latitude', 'longitude', 'location_address']

# Blood Camp Forms
class BloodCampForm(forms.ModelForm):
    class Meta:
        model = models.BloodCamp
        fields = [
            'name', 'description', 'organizer', 'sponsor', 'hospital_partner',
            'venue', 'address', 'city', 'state',
            'start_date', 'end_date', 'start_time', 'end_time',
            'target_donors', 'status'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class CampRegistrationForm(forms.ModelForm):
    class Meta:
        model = models.CampRegistration
        fields = ['camp']
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Only show upcoming camps
            self.fields['camp'].queryset = models.BloodCamp.objects.filter(
                status='PLANNED'
            ).order_by('start_date')

# Sponsor and Hospital Forms
class SponsorForm(forms.ModelForm):
    class Meta:
        model = models.Sponsor
        fields = [
            'name', 'logo', 'description', 'website',
            'contact_email', 'contact_phone', 'address',
            'city', 'state', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class HospitalForm(forms.ModelForm):
    class Meta:
        model = models.Hospital
        fields = [
            'name', 'address', 'city', 'state',
            'contact_phone', 'contact_email', 'emergency_contact',
            'blood_bank_available', 'is_partner'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }
