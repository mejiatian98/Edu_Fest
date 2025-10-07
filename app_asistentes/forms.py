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



    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except forms.ValidationError as e:
            # Eliminamos los errores de unicidad de username y email.
            e.error_dict.pop('username', None)
            e.error_dict.pop('email', None)
            
            # Si aún quedan otros errores (ej: first_name, last_name, id), los lanzamos.
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
