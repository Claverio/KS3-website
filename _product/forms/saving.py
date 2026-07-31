import re
from decimal import Decimal

from django import forms

from _product.models import Product, SavingTransaction


class SavingTransactionForm(forms.ModelForm):
    amount = forms.DecimalField(
        min_value=Decimal("1"),
        max_digits=18,
        decimal_places=0,
        label="Nominal setoran",
        error_messages={
            "required": "Nominal setoran wajib diisi.",
            "invalid": "Nominal setoran harus berupa angka.",
            "min_value": "Nominal setoran harus lebih dari Rp0.",
        },
        widget=forms.NumberInput(
            attrs={"min": 1, "step": 1, "inputmode": "numeric", "placeholder": "cth: 500000"}
        ),
    )

    class Meta:
        model = SavingTransaction
        fields = (
            "product",
            "is_new_member",
            "nomor_anggota",
            "full_name",
            "phone",
            "email",
            "nik",
            "amount",
            "note",
        )
        labels = {
            "product": "Jenis simpanan",
            "is_new_member": "Saya anggota baru dan belum memiliki nomor anggota",
            "nomor_anggota": "Nomor anggota",
            "full_name": "Nama lengkap (sesuai KTP)",
            "phone": "No. handphone / WhatsApp",
            "email": "Email",
            "nik": "NIK",
            "note": "Catatan untuk admin",
        }
        widgets = {
            "product": forms.Select(),
            "is_new_member": forms.CheckboxInput(
                attrs={"class": "form-check-input ks3-saving-member-check"}
            ),
            "nomor_anggota": forms.TextInput(
                attrs={"placeholder": "cth: AGT-00123", "autocomplete": "off", "maxlength": 50}
            ),
            "full_name": forms.TextInput(
                attrs={
                    "placeholder": "cth: Budi Santoso",
                    "autocomplete": "name",
                    "minlength": 3,
                    "maxlength": 255,
                    "pattern": r"[^0-9]*",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "type": "tel",
                    "placeholder": "cth: 0812 3456 7890",
                    "autocomplete": "tel",
                    "inputmode": "tel",
                    "maxlength": 24,
                }
            ),
            "email": forms.EmailInput(
                attrs={"placeholder": "cth: budi@email.com", "autocomplete": "email"}
            ),
            "nik": forms.TextInput(
                attrs={
                    "placeholder": "16 digit nomor KTP",
                    "inputmode": "numeric",
                    "minlength": 16,
                    "maxlength": 16,
                }
            ),
            "note": forms.Textarea(
                attrs={"rows": 3, "maxlength": 1000, "placeholder": "Catatan tambahan (opsional)"}
            ),
        }
        error_messages = {
            "product": {"required": "Jenis simpanan wajib dipilih."},
            "full_name": {"required": "Nama lengkap wajib diisi."},
            "phone": {"required": "Nomor WhatsApp wajib diisi."},
            "email": {
                "required": "Email wajib diisi.",
                "invalid": "Masukkan alamat email yang valid.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(
            is_published=True,
            category__is_active=True,
            category__slug="simpanan",
        ).select_related("category").order_by("sort_order", "title")
        for name, field in self.fields.items():
            if name == "is_new_member":
                continue
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
            raise forms.ValidationError("Masukkan 8-15 digit nomor WhatsApp yang valid.")
        return phone

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_nik(self):
        nik = self.cleaned_data.get("nik", "").strip()
        if nik and not re.fullmatch(r"\d{16}", nik):
            raise forms.ValidationError("NIK harus terdiri dari tepat 16 digit.")
        return nik

    def clean_note(self):
        return self.cleaned_data.get("note", "").strip()

    def clean(self):
        cleaned = super().clean()
        is_new_member = cleaned.get("is_new_member", False)
        nomor_anggota = cleaned.get("nomor_anggota", "").strip()
        if is_new_member:
            cleaned["nomor_anggota"] = ""
        elif not nomor_anggota:
            self.add_error("nomor_anggota", "Nomor anggota wajib diisi untuk anggota lama.")
        return cleaned
