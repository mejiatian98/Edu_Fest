# En tu archivo forms.py

from django import forms
from app_usuarios.models import Usuario, Participante
from .models import ParticipanteEvento

class ParticipanteForm(forms.ModelForm):
    par_id = forms.IntegerField(
        label="Cédula",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingresa tu número de cédula'})
    )
    
    class Meta:
        model = Usuario
        fields = ['par_id', 'username', 'email', 'telefono', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@email.com'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de teléfono'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu apellido'}),
        }

    def __init__(self, *args, **kwargs):
        # Extraer el evento si se pasa como parámetro
        self.evento = kwargs.pop('evento', None)
        super().__init__(*args, **kwargs)

    def clean_par_id(self):
        par_id = self.cleaned_data['par_id']
        
        # Solo validar si hay un evento específico
        if self.evento:
            # Verificar si ya está registrado en este evento específico
            participante_existente = Participante.objects.filter(par_id=par_id).first()
            if participante_existente:
                if ParticipanteEvento.objects.filter(
                    par_eve_participante_fk=participante_existente,
                    par_eve_evento_fk=self.evento
                ).exists():
                    raise forms.ValidationError(
                        f"Ya existe un participante con la cédula {par_id} registrado para este evento."
                    )
        
        return par_id

    def clean_username(self):
        username = self.cleaned_data['username']
        
        # Solo validar username para nuevos usuarios
        if self.evento:
            # Verificar si existe un participante con la cédula del formulario
            par_id = self.cleaned_data.get('par_id')
            if par_id:
                participante_existente = Participante.objects.filter(par_id=par_id).first()
                if participante_existente:
                    # Si el participante existe, no validar username
                    return username
        
        # Validar username solo para nuevos usuarios
        if Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está registrado.")
        
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        
        # Solo validar email para nuevos usuarios
        if self.evento:
            # Verificar si existe un participante con la cédula del formulario
            par_id = self.cleaned_data.get('par_id')
            if par_id:
                participante_existente = Participante.objects.filter(par_id=par_id).first()
                if participante_existente:
                    # Si el participante existe, no validar email
                    return email
        
        # Validar email solo para nuevos usuarios
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        
        return email


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