from django import forms


class ChatMessageForm(forms.Form):
    """Form for chat message input"""
    message = forms.CharField(
        max_length=1000,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Type your message here...',
            'autocomplete': 'off',
            'maxlength': '1000'
        }),
        label='',
        required=True
    )
    
    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if not message:
            raise forms.ValidationError('Message cannot be empty.')
        return message