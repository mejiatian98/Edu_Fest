# En tu archivo forms.py

from django import forms
from app_usuarios.models import Usuario, Participante
from .models import ParticipanteEvento


class ParticipanteForm(forms.ModelForm):
    # Campo para la cédula (id)
    id = forms.IntegerField(
        label="Cédula",
        widget=forms.NumberInput(
            attrs={'class': 'form-control', 'placeholder': 'Ingresa tu número de cédula'}
        )
    )

    # Campos de Usuario
    username = forms.CharField(
        label="Nombre de usuario",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'})
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@email.com'})
    )
    telefono = forms.CharField(
        label="Teléfono",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de teléfono'})
    )
    first_name = forms.CharField(
        label="Nombre",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'})
    )
    last_name = forms.CharField(
        label="Apellido",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu apellido'})
    )

    class Meta:
        model = Participante
        fields = ['id']  # El único campo que pertenece directamente al modelo Participante

    def __init__(self, *args, **kwargs):
        self.evento = kwargs.pop('evento', None)
        super().__init__(*args, **kwargs)

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except forms.ValidationError as e:
            # Eliminamos errores de unicidad ajenos al flujo actual
            e.error_dict.pop('id', None)
            if e.error_dict:
                raise


    def clean_id(self):
        id_value = self.cleaned_data['id']
        return str(id_value).strip()





# Agregar la clase que falta
class EditarUsuarioParticipanteForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefono']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }