from django import forms
from django.utils import timezone

from .models import EsCfgForm
from .pricing import PRICE_CHOICES, PRICE_INR_499


class PaidPrescriptionForm(forms.Form):
    form_code = forms.ModelChoiceField(queryset=EsCfgForm.objects.filter(is_active=True), to_field_name="form_code")
    price_variant = forms.ChoiceField(choices=PRICE_CHOICES)
    patient_name = forms.CharField(max_length=255)
    patient_whatsapp = forms.CharField(max_length=20)
    patient_email = forms.EmailField(required=False)
    discount_percent = forms.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100, required=False)

    def clean(self):
        data = super().clean()
        discount_percent = data.get("discount_percent") or 0
        if data.get("price_variant") != PRICE_INR_499 and discount_percent:
            self.add_error("discount_percent", "Discount is available only for the ₹499 form amount.")
        return data


class PatientEmailForm(forms.Form):
    patient_email = forms.EmailField()


class DemographicsForm(forms.Form):
    child_name = forms.CharField(max_length=255)
    child_dob = forms.DateField(required=True, widget=forms.DateInput(attrs={"type": "date"}))
    assessment_date = forms.DateField(required=True, widget=forms.DateInput(attrs={"type": "date"}))
    gender = forms.ChoiceField(choices=[("male", "Male"), ("female", "Female"), ("other", "Other")])
    completed_by = forms.CharField(max_length=255)
    consent_given = forms.BooleanField(required=True)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate().isoformat()
        self.fields["child_dob"].widget.attrs["max"] = today
        self.fields["assessment_date"].widget.attrs["max"] = today
