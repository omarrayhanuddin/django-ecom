from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(max_length=120, label="নাম")
    email = forms.EmailField(label="ইমেইল")
    subject = forms.CharField(max_length=150, label="বিষয়")
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label="বার্তা")
