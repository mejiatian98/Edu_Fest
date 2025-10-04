from django import forms
from app_usuarios.models import Usuario, Evaluador
from app_evaluadores.models import EvaluadorEvento


class EvaluadorForm(forms.ModelForm):
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
        self.evento = kwargs.pop('evento', None)  # 🔹 Guardamos el evento que viene desde la vista
        super().__init__(*args, **kwargs)

    def clean_id(self):
        """
        Verifica que la cédula no esté repetida en el mismo evento.
        Pero permite inscribirse en diferentes eventos con la misma cédula.
        """
        id = self.cleaned_data['id']
        if self.evento:
            evaluador_existente = Evaluador.objects.filter(id=id).first()
            if evaluador_existente and EvaluadorEvento.objects.filter(
                eva_eve_evaluador_fk=evaluador_existente,
                eva_eve_evento_fk=self.evento
            ).exists():
                raise forms.ValidationError(
                    f"Ya existe un evaluador con la cédula {id} registrado para este evento."
                )
        return id

    def clean_username(self):
        """
        Permite reutilizar el mismo username si ya existe en la BD.
        Solo se bloquea en la lógica de la vista si intenta inscribirse en el mismo evento.
        """
        username = self.cleaned_data['username']
        return username

    def clean_email(self):
        """
        Igual que con username: el mismo correo puede ser usado en diferentes eventos.
        """
        email = self.cleaned_data['email']
        return email

    def validate_unique(self):
        """
        Sobrescribimos la validación de unicidad para que Django no bloquee
        por username/email duplicados en la tabla Usuario.
        """
        pass





# Form para editar
class EditarUsuarioEvaluadorForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefono']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }
