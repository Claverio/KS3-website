import re

from django import forms

from _p2p.models import P2PPurchase


class P2PPurchaseForm(forms.ModelForm):
    slot_quantity = forms.IntegerField(
        min_value=1,
        label="Jumlah slot",
        error_messages={
            "required": "Jumlah slot wajib diisi.",
            "invalid": "Jumlah slot harus berupa angka bulat.",
            "min_value": "Jumlah slot minimal 1.",
        },
        widget=forms.NumberInput(attrs={"min": 1, "step": 1, "inputmode": "numeric"}),
    )

    class Meta:
        model = P2PPurchase
        fields = ("full_name", "phone", "email", "nik", "slot_quantity", "note")
        labels = {
            "full_name": "Nama lengkap (sesuai KTP)",
            "phone": "No. handphone / WhatsApp",
            "email": "Email",
            "nik": "NIK",
            "note": "Catatan untuk admin",
        }
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "placeholder": "cth: Budi Santoso",
                    "autocomplete": "name",
                    "minlength": 3,
                    "maxlength": 255,
                    "pattern": r"[^0-9]*",
                    "title": "Nama lengkap tidak boleh mengandung angka.",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "type": "tel",
                    "placeholder": "cth: 0812 3456 7890",
                    "autocomplete": "tel",
                    "inputmode": "tel",
                    "pattern": r"\+?[0-9][0-9\s-]{7,19}",
                    "maxlength": 24,
                    "title": "Masukkan 8–15 digit nomor WhatsApp yang valid.",
                }
            ),
            "email": forms.EmailInput(
                attrs={"placeholder": "cth: budi@email.com", "autocomplete": "email"}
            ),
            "nik": forms.TextInput(
                attrs={
                    "placeholder": "16 digit nomor KTP",
                    "inputmode": "numeric",
                    "pattern": r"[0-9]{16}",
                    "minlength": 16,
                    "maxlength": 16,
                    "title": "NIK harus terdiri dari tepat 16 digit.",
                }
            ),
            "note": forms.Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": 1000,
                    "placeholder": "cth: konfirmasi via WhatsApp",
                }
            ),
        }
        error_messages = {
            "full_name": {"required": "Nama lengkap wajib diisi."},
            "phone": {
                "required": "Nomor handphone / WhatsApp wajib diisi.",
                "invalid": "Masukkan 8–15 digit nomor WhatsApp yang valid.",
            },
            "email": {
                "required": "Email wajib diisi.",
                "invalid": "Masukkan alamat email yang valid.",
            },
            "nik": {"invalid": "NIK harus terdiri dari tepat 16 digit."},
        }

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.fields["slot_quantity"].widget.attrs["max"] = project.available_slots
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control border-radius-4px box-shadow-double-large"
            if self.is_bound and self.errors.get(name):
                field.widget.attrs["class"] += " is-invalid"
                field.widget.attrs["aria-invalid"] = "true"

    def clean_full_name(self):
        name = " ".join(self.cleaned_data["full_name"].split())
        if len(name) < 3 or not any(character.isalpha() for character in name):
            raise forms.ValidationError("Nama lengkap minimal 3 karakter.")
        if any(character.isdigit() for character in name):
            raise forms.ValidationError("Nama lengkap tidak boleh mengandung angka.")
        return name

    def clean_phone(self):
        phone = re.sub(r"[\s-]+", "", self.cleaned_data["phone"].strip())
        if not re.fullmatch(r"\+?\d{8,15}", phone):
            raise forms.ValidationError("Masukkan 8–15 digit nomor WhatsApp yang valid.")
        return phone

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_nik(self):
        nik = self.cleaned_data.get("nik", "").strip()
        if nik and not re.fullmatch(r"\d{16}", nik):
            raise forms.ValidationError("NIK harus terdiri dari tepat 16 digit.")
        return nik

    def clean_note(self):
        note = self.cleaned_data.get("note", "").strip()
        if len(note) > 1000:
            raise forms.ValidationError("Catatan maksimal 1.000 karakter.")
        return note

    def clean_slot_quantity(self):
        quantity = self.cleaned_data["slot_quantity"]
        if quantity > self.project.available_slots:
            raise forms.ValidationError("Slot tersedia tidak mencukupi.")
        return quantity
