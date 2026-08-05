from django import forms

from .models import XenditFeeAdjustment


class XenditFeeAdjustmentPostForm(forms.ModelForm):
    class Meta:
        model = XenditFeeAdjustment
        fields = ("amount", "kind", "reason", "external_reference")
        labels = {
            "amount": "Nominal adjustment",
            "kind": "Jenis adjustment",
            "reason": "Alasan",
            "external_reference": "Referensi eksternal",
        }
        help_texts = {
            "amount": (
                "Positif menutup fee yang kurang dibebankan; negatif menutup fee yang "
                "kelebihan dibebankan. Satu adjustment dialokasikan FIFO ke banyak transaksi."
            ),
        }
        widgets = {
            "amount": forms.NumberInput(attrs={"step": "1"}),
            "reason": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount == 0:
            raise forms.ValidationError("Nominal adjustment tidak boleh nol.")
        return amount
