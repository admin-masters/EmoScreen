from django import forms
from .models import RegisteredProfessional
from .utils import normalize_phone
from .state_districts import state_choices, district_choices, is_valid_pair

SALUTATIONS = [("Dr", "Dr."), ("Mr", "Mr."), ("Ms", "Ms."), ("Mrs", "Mrs.")]

class PediatricianForm(forms.ModelForm):
    class Meta:
        model = RegisteredProfessional
        fields = [
            "salutation", "first_name", "last_name", "email", "whatsapp",
            "imc_registration_number", "appointment_booking_number",
            "clinic_address", "state", "district",
            "receptionist_whatsapp", "photo_url"
        ]
        widgets = {
            "salutation": forms.Select(choices=[("Dr", "Dr.")]),
            "clinic_address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All required except receptionist_whatsapp and photo_url
        for name, field in self.fields.items():
            field.required = name not in ("receptionist_whatsapp", "photo_url")

        # Make state a select with all states; district depends on state
        sel_state = (self.data.get("state")
                     or self.initial.get("state")
                     or "")
        self.fields["state"].widget = forms.Select(choices=state_choices())
        self.fields["district"].widget = forms.Select(choices=district_choices(sel_state))
        self.fields["district"].required = True

    def clean_whatsapp(self):
        return normalize_phone(self.cleaned_data["whatsapp"])

    def clean_appointment_booking_number(self):
        return normalize_phone(self.cleaned_data["appointment_booking_number"])

    def clean_receptionist_whatsapp(self):
        val = self.cleaned_data.get("receptionist_whatsapp")
        return normalize_phone(val) if val else val

    def clean(self):
        data = super().clean()
        # If receptionist no. left blank → copy doctor’s WhatsApp
        if not data.get("receptionist_whatsapp"):
            data["receptionist_whatsapp"] = data.get("whatsapp")

        # Validate state/district pair; enforce NULL rule
        state = (data.get("state") or "").strip()
        district = (data.get("district") or "").strip()
        if state == "NULL":
            data["district"] = "NULL"
            district = "NULL"
        if not is_valid_pair(state, district):
            self.add_error("district", "Please choose a district that belongs to the selected state.")
        return data


class CaregiverForm(forms.ModelForm):
    name = forms.CharField(label="Name of Caregiver")

    class Meta:
        model = RegisteredProfessional
        fields = [
            "salutation", "email", "whatsapp", "appointment_booking_number",
            "clinic_address", "state", "district", "receptionist_whatsapp", "photo_url"
        ]
        widgets = {
            "salutation": forms.Select(choices=SALUTATIONS),
            "clinic_address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All required except receptionist and photo
        self.fields["name"].required = True
        for name, field in self.fields.items():
            field.required = name not in ("receptionist_whatsapp", "photo_url")

        sel_state = (self.data.get("state")
                     or self.initial.get("state")
                     or "")
        self.fields["state"].widget = forms.Select(choices=state_choices())
        self.fields["district"].widget = forms.Select(choices=district_choices(sel_state))
        self.fields["district"].required = True

    def clean_whatsapp(self):
        return normalize_phone(self.cleaned_data["whatsapp"])

    def clean_appointment_booking_number(self):
        return normalize_phone(self.cleaned_data["appointment_booking_number"])

    def clean_receptionist_whatsapp(self):
        val = self.cleaned_data.get("receptionist_whatsapp")
        return normalize_phone(val) if val else val

    def clean(self):
        data = super().clean()
        if not data.get("receptionist_whatsapp"):
            data["receptionist_whatsapp"] = data.get("whatsapp")

        state = (data.get("state") or "").strip()
        district = (data.get("district") or "").strip()
        if state == "NULL":
            data["district"] = "NULL"
            district = "NULL"
        if not is_valid_pair(state, district):
            self.add_error("district", "Please choose a district that belongs to the selected state.")
        return data


class ClinicSendForm(forms.Form):
    parent_whatsapp = forms.CharField(label="Parent WhatsApp", max_length=20)
    language = forms.ChoiceField(choices=[], label="Select Language")

    def __init__(self, *args, **kwargs):
        # view passes lang_choices=[("en","English"), ...]
        lang_choices = kwargs.pop("lang_choices", [])
        super().__init__(*args, **kwargs)
        self.fields["language"].choices = lang_choices

    def clean_parent_whatsapp(self):
        return normalize_phone(self.cleaned_data["parent_whatsapp"])

# content/forms.py  (append)

class BulkDoctorUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Upload CSV (max 100 rows)",
        help_text="CSV must include Doctor Name, WhatsApp Number, Email ID, IMC Registration Number. "
                  "Optional: Clinic Appointment Booking Number, Clinic Address with Postal Code, "
                  "State, District, Receptionist WhatsApp Number, Receptionist Email ID, Doctor’s Photo."
    )

    def clean_csv_file(self):
        f = self.cleaned_data["csv_file"]
        if not f.name.lower().endswith(".csv"):
            raise forms.ValidationError("Please upload a .csv file")
        # 2 MB soft limit is generous for 100 rows
        if f.size > 2 * 1024 * 1024:
            raise forms.ValidationError("CSV too large (limit ~2MB)")
        return f



