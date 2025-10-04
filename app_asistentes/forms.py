from django import forms
from app_usuarios.models import Usuario, Asistente
from .models import AsistenteEvento

class AsistenteForm(forms.ModelForm):
    id = forms.IntegerField(
        label="Cédula",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingresa tu número de cédula'})
    )

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'telefono', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@email.com'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de teléfono'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu apellido'}),
        }

    def __init__(self, *args, **kwargs):
        self.evento = kwargs.pop('evento', None)
        super().__init__(*args, **kwargs)

    def clean_id(self):
        id = self.cleaned_data['id']
        if self.evento:
            asistente_existente = Asistente.objects.filter(id=id).first()
            if asistente_existente and AsistenteEvento.objects.filter(
                asi_eve_asistente_fk=asistente_existente,
                asi_eve_evento_fk=self.evento
            ).exists():
                raise forms.ValidationError(
                    f"Ya existe un asistente con la cédula {id} registrado para este evento."
                )
        return id

    def clean_username(self):
        username = self.cleaned_data['username']
        id = self.cleaned_data.get('id')
        asistente_existente = Asistente.objects.filter(id=id).first()
        if asistente_existente:
            return username
        if Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está registrado.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        id = self.cleaned_data.get('id')
        asistente_existente = Asistente.objects.filter(id=id).first()
        if asistente_existente:
            return email
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return email

    def validate_unique(self):
        """
        Sobrescribe la validación de unicidad para que no moleste
        cuando reutilizamos un usuario existente.
        """
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except forms.ValidationError as e:
            e.error_dict.pop('username', None)
            e.error_dict.pop('email', None)
            if e.error_dict:
                raise




# Form para editar
class EditarUsuarioAsistenteForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefono']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }
