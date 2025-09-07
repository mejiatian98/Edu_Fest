from django import forms
from .models import Evento, Categoria, Area
from app_usuarios.models import Usuario



class EventoForm(forms.ModelForm):
    area = forms.ModelChoiceField(
        queryset=Area.objects.all(),
        required=True,
        label="Área"
    )

    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'id': 'id_categoria'}),
        required=True,
        label="Categorías"
    )

    class Meta:
        model = Evento
        fields = [
            'eve_nombre', 'eve_descripcion', 'eve_ciudad', 'eve_lugar', 'eve_fecha_inicio',
            'eve_fecha_fin', 'eve_estado', 'eve_imagen', 'eve_tienecosto',
            'eve_capacidad', 'eve_programacion'
        ]
        labels = {
            'eve_nombre': 'Título del evento',
            'eve_descripcion': 'Descripción',
            'eve_ciudad': 'Ciudad',
            'eve_lugar': 'Lugar',
            'eve_fecha_inicio': 'Fecha de inicio',
            'eve_fecha_fin': 'Fecha de fin',
            'eve_estado': 'Estado',
            'eve_imagen': 'Imagen del evento',
            'eve_tienecosto': '¿Tiene costo?',
            'eve_capacidad': 'Capacidad de personas',
            'eve_programacion': 'Archivo de programación',
        }
        widgets = {
            'eve_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'eve_descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'eve_ciudad': forms.TextInput(attrs={'class': 'form-control'}),
            'eve_lugar': forms.TextInput(attrs={'class': 'form-control'}),
            'eve_fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'eve_fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'eve_estado': forms.TextInput(attrs={'class': 'form-control'}),
            'eve_imagen': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'eve_programacion': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'eve_capacidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'eve_tienecosto': forms.Select(attrs={'class': 'form-control'}),
        }


class EditarUsuarioAdministradorForm(forms.ModelForm):
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
        if Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está registrado.")
        return username