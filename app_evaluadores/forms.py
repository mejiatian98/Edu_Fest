from django import forms
from app_usuarios.models import Usuario, Evaluador

class EvaluadorForm(forms.ModelForm):
    id = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su cédula',
            'type': 'number',
            'min': '1'
        }),
        label='Cédula',
        required=True
    )

    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese nombre de usuario'}),
        label='Nombre de usuario',
        required=True
    )

    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su nombre'}),
        label='Nombre',
        required=True
    )

    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su apellido'}),
        label='Apellido',
        required=True
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su correo'}),
        label='Correo',
        required=True
    )

    telefono = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su teléfono', 'type': 'number'}),
        label='Teléfono',
        required=False
    )

    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'telefono']

    def clean_id(self):
        id = self.cleaned_data['id']
        if not id.isdigit():
            raise forms.ValidationError("La cédula debe contener solo números.")
        if Evaluador.objects.filter(id=id).exists():
            raise forms.ValidationError("Esta cédula ya está registrada.")
        return id

    def clean_email(self):
        email = self.cleaned_data['email']
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está registrado.")
        return username


class EditarUsuarioEvaluadorForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'telefono']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese nombre de usuario'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su apellido'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su teléfono', 'type': 'number'}),
        }

    def clean_username(self):
        username = self.cleaned_data['username']
        if Usuario.objects.filter(username=username).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("Este nombre de usuario ya está registrado.")
        return username
