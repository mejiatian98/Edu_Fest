

import datetime
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

# Importar modelos necesarios de la base de datos bd_edufest
from app_usuarios.models import Usuario, AdministradorEvento
from app_admin_eventos.models import Evento, Criterio, Categoria, Area




class ListarEventosPublicosViewTest(TestCase):
    """
    Pruebas para la vista pública que lista los eventos próximos.
    Cubre la HU-01.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Configura los datos iniciales para todas las pruebas de esta clase.
        Se ejecuta una sola vez.
        """
        # Crear un usuario administrador para asociarlo a los eventos
        cls.admin_user = Usuario.objects.create_user(
            username='admin_evento', 
            password='password123', 
            rol=Usuario.Roles.ADMIN_EVENTO
        )
        cls.administrador = AdministradorEvento.objects.get_or_create(
            id=1,
            usuario=cls.admin_user
        )

        # Crear archivos dummy para los campos FileField/ImageField
        dummy_image = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        dummy_file = SimpleUploadedFile("test_program.pdf", b"file_content", content_type="application/pdf")

        # Definir fechas relativas al día de hoy para que las pruebas sean determinísticas
        hoy = timezone.now().date()
        
        # 1. Evento que ya finalizó (NO debe mostrarse)
        Evento.objects.create(
            eve_nombre='Evento Pasado',
            eve_fecha_inicio=hoy - datetime.timedelta(days=10),
            eve_fecha_fin=hoy - datetime.timedelta(days=5),
            eve_estado='Activo',
            eve_administrador_fk=cls.administrador,
            eve_imagen=dummy_image,
            eve_programacion=dummy_file,
            eve_ciudad='Ciudad Pasada',
            eve_lugar='Lugar Pasado',
            eve_capacidad=100,
            eve_tienecosto='No'
        )

        # 2. Evento futuro y activo (DEBE mostrarse)
        cls.evento_futuro = Evento.objects.create(
            eve_nombre='Evento Futuro Lejano',
            eve_fecha_inicio=hoy + datetime.timedelta(days=30),
            eve_fecha_fin=hoy + datetime.timedelta(days=32),
            eve_estado='Activo',
            eve_administrador_fk=cls.administrador,
            eve_imagen=dummy_image,
            eve_programacion=dummy_file,
            eve_ciudad='Ciudad Futura',
            eve_lugar='Lugar Futuro',
            eve_capacidad=100,
            eve_tienecosto='No'
        )

        # 3. Evento próximo y activo (DEBE mostrarse y aparecer primero)
        cls.evento_proximo = Evento.objects.create(
            eve_nombre='Evento Muy Próximo',
            eve_fecha_inicio=hoy + datetime.timedelta(days=2),
            eve_fecha_fin=hoy + datetime.timedelta(days=4),
            eve_estado='Activo',
            eve_administrador_fk=cls.administrador,
            eve_imagen=dummy_image,
            eve_programacion=dummy_file,
            eve_ciudad='Ciudad Próxima',
            eve_lugar='Lugar Próximo',
            eve_capacidad=100,
            eve_tienecosto='No'
        )

        # 4. Evento futuro pero en estado 'Cancelado' (NO debe mostrarse)
        Evento.objects.create(
            eve_nombre='Evento Futuro Cancelado',
            eve_fecha_inicio=hoy + datetime.timedelta(days=15),
            eve_fecha_fin=hoy + datetime.timedelta(days=16),
            eve_estado='Cancelado',
            eve_administrador_fk=cls.administrador,
            eve_imagen=dummy_image,
            eve_programacion=dummy_file,
            eve_ciudad='Ciudad Cancelada',
            eve_lugar='Lugar Cancelado',
            eve_capacidad=100,
            eve_tienecosto='No'
        )

        cls.url = reverse('lista_eventos_publica') # Asumiendo que la URL se llama así

    def test_acceso_y_plantilla_correcta(self):
        """Verifica que la página carga correctamente para un visitante."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # self.assertTemplateUsed(response, 'eventos/lista_publica.html') # Descomentar si se conoce el nombre de la plantilla

    def test_muestra_eventos_proximos_y_activos(self):
        """Prueba AC-01: Verifica que solo los eventos activos y futuros se listan."""
        response = self.client.get(self.url)
        # Verifica que los eventos correctos están en el contexto de la plantilla
        self.assertIn('eventos', response.context)
        eventos_en_contexto = response.context['eventos']
        
        self.assertEqual(len(eventos_en_contexto), 2)
        nombres_eventos = [evento.eve_nombre for evento in eventos_en_contexto]
        self.assertIn(self.evento_proximo.eve_nombre, nombres_eventos)
        self.assertIn(self.evento_futuro.eve_nombre, nombres_eventos)

    def test_no_muestra_eventos_pasados(self):
        """Prueba AC-02: Verifica que eventos con fecha de fin pasada no se muestran."""
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Evento Pasado')

    def test_no_muestra_eventos_no_activos(self):
        """Prueba AC-03: Verifica que eventos en estado 'Cancelado' no se muestran."""
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Evento Futuro Cancelado')

    def test_eventos_ordenados_cronologicamente(self):
        """Prueba AC-04: Verifica el orden de los eventos por fecha de inicio."""
        response = self.client.get(self.url)
        eventos_en_contexto = response.context['eventos']
        
        self.assertEqual(len(eventos_en_contexto), 2)
        # El primero en la lista debe ser el más próximo
        self.assertEqual(eventos_en_contexto[0].eve_nombre, 'Evento Muy Próximo')
        # El segundo debe ser el más lejano
        self.assertEqual(eventos_en_contexto[1].eve_nombre, 'Evento Futuro Lejano')

    def test_muestra_mensaje_cuando_no_hay_eventos_visibles(self):
        """Prueba AC-05: Verifica que se muestra un mensaje si no hay eventos."""
        # Borramos todos los eventos para simular un estado vacío
        Evento.objects.all().delete()
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hay eventos próximos disponibles en este momento")
        # El contexto de eventos debe estar vacío
        self.assertEqual(len(response.context['eventos']), 0)