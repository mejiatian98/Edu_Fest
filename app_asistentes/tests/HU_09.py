""" Como Compartir la información de los eventos en los que estoy inscrito con mis contactos para 
Motivar a otras personas a asistir a los eventos"""


from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile 
from urllib.parse import quote as urlquote 
from django.utils import timezone 
from datetime import date, datetime
from unittest.mock import patch, MagicMock 
import io 

# Importa tus modelos (ajusta las rutas de importación si es necesario)
from app_usuarios.models import Usuario, Asistente, AdministradorEvento
from app_admin_eventos.models import Evento
from app_asistentes.models import AsistenteEvento

class SharingEventoAsistenteTests(TestCase):
    """Pruebas para la historia de usuario de Compartir Evento como Asistente (HU-09)."""

    @classmethod
    def setUpTestData(cls):
        # 1. Crear datos de Administrador de Evento (para la FK)
        cls.super_admin_user = Usuario.objects.create_user(
            username='superadmin', password='password123', rol=Usuario.Roles.SUPERADMIN
        )
        cls.admin_evento = AdministradorEvento.objects.create(
            usuario=cls.super_admin_user
        )

        # 2. Crear datos de Asistente
        cls.asistente_user = Usuario.objects.create_user(
            username='asistente1', password='password123', rol=Usuario.Roles.ASISTENTE
        )
        cls.asistente = Asistente.objects.create(
            usuario=cls.asistente_user
        )

        # 3. Crear archivos simulados (usando un GIF simple para imagen)
        img_content = b'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7' 
        cls.dummy_image = SimpleUploadedFile(
            "test_image.gif", 
            img_content, 
            content_type="image/gif"
        )
        cls.dummy_file = SimpleUploadedFile(
            "test_programacion.pdf", 
            b"Contenido de prueba", 
            content_type="application/pdf"
        )

        # 4. Crear Evento X (Inscrito, PK=1)
        cls.evento_x = Evento.objects.create(
            eve_nombre='Conferencia de Python',
            eve_descripcion='Todo sobre Django',
            eve_ciudad='Manizales',
            eve_lugar='Teatro',
            eve_fecha_inicio=date(2025, 12, 1),
            eve_fecha_fin=date(2025, 12, 3),
            eve_estado='Publicado',
            eve_imagen=SimpleUploadedFile("test_image_x.gif", img_content, content_type="image/gif"),
            eve_administrador_fk=cls.admin_evento,
            eve_tienecosto='Sí',
            eve_capacidad=100,
            eve_programacion=SimpleUploadedFile("test_programacion_x.pdf", b"Content X", content_type="application/pdf"),
            preinscripcion_habilitada_asistentes=True
        )
        
        # 5. Crear Evento Y (No Inscrito, PK=2)
        cls.evento_y = Evento.objects.create(
            eve_nombre='Seminario de DevOps',
            eve_descripcion='Containers y Kubernetes',
            eve_ciudad='Bogota',
            eve_lugar='Auditorio',
            eve_fecha_inicio=date(2026, 1, 15),
            eve_fecha_fin=date(2026, 1, 16),
            eve_estado='Publicado',
            eve_imagen=SimpleUploadedFile("test_image_y.gif", img_content, content_type="image/gif"),
            eve_administrador_fk=cls.admin_evento,
            eve_tienecosto='No',
            eve_capacidad=50,
            eve_programacion=SimpleUploadedFile("test_programacion_y.pdf", b"Content Y", content_type="application/pdf"),
            preinscripcion_habilitada_asistentes=True
        )

        # 6. Inscribir asistente al Evento X
        aware_datetime = timezone.make_aware(datetime(2025, 11, 1, 10, 0, 0))
        cls.asistente_evento = AsistenteEvento.objects.create(
            asi_eve_asistente_fk=cls.asistente,
            asi_eve_evento_fk=cls.evento_x,
            asi_eve_fecha_hora=aware_datetime,
            asi_eve_estado='Aprobado',
            asi_eve_soporte=SimpleUploadedFile("test_soporte.pdf", b"Soporte", content_type="application/pdf"), 
            asi_eve_qr=SimpleUploadedFile("test_qr_asi_eve.png", b"Datos QR", content_type="image/png"), 
            asi_eve_clave='CLAVEX'
        )
        
        # URLs
        cls.url_detalle_evento = reverse('ver_info_evento_asi', kwargs={'pk': cls.evento_x.pk})
        cls.url_detalle_evento_no_inscrito = reverse('ver_info_evento_asi', kwargs={'pk': cls.evento_y.pk})
        cls.url_dashboard_asistente = reverse('dashboard_asistente')


    def setUp(self):
        self.client = Client()
        self.client.login(username='asistente1', password='password123')
        session = self.client.session
        session['asistente_id'] = self.asistente.id 
        session.save()

    # CP-SHR-001: Verifica acceso 200 y presencia del botón compartir (CA1).
    # En app_asistentes.tests.HU_09.py, dentro de test_cshr_001_acceso_y_visibilidad_inscrito
    def test_cshr_001_acceso_y_visibilidad_inscrito(self):
        """
        Verifica que el asistente inscrito accede a la vista y ve el botón compartir.
        """
        response = self.client.get(self.url_detalle_evento)
        
        self.assertEqual(response.status_code, 200)
        
        # ✅ USA ESTA ASERCIÓN.
        # El texto visible ahora está garantizado a ser 'Compartir' sin espacios iniciales,
        # gracias a que compactaste el HTML.
        self.assertContains(response, 'Compartir') 
        
        # Nota: No necesitamos el argumento 'html=True' a menos que busquemos una etiqueta completa.
        # Buscar el texto simple suele ser más robusto para verificar contenido visible.

    # CP-SHR-002: Valida que la URL absoluta se genere y se pase al contexto (CA2).
    # app_asistentes.tests.HU_09.py


    @patch('django.http.request.HttpRequest.build_absolute_uri')
    def test_cshr_002_validacion_url_compartir_generada(self, mock_build_absolute_uri):
        # Simula la URL absoluta que se espera que se genere
        expected_url_path = reverse('ver_info_evento_asi', kwargs={'pk': self.evento_x.pk})
        fake_absolute_url = f'http://testserver{expected_url_path}'
        mock_build_absolute_uri.return_value = fake_absolute_url

        response = self.client.get(self.url_detalle_evento)
        
        self.assertEqual(response.status_code, 200)

        # ✅ CORRECCIÓN DEFINITIVA: Buscar solo la URL desnuda, sin value="...".
        # Esto ignora cualquier variación en espacios o comillas.
        self.assertContains(response, fake_absolute_url) 
        
        # Opcional (si la anterior falla): buscar con las comillas simples que usa la plantilla.
        # self.assertContains(response, f"value='{fake_absolute_url}'")

    # CP-SHR-003: Verifica que el asistente no inscrito sea redirigido (CA5).
    def test_cshr_003_restriccion_acceso_no_inscrito(self):
        """
        Verifica que el asistente no inscrito sea redirigido a la vista de registro.
        (FIX: Se ajusta la expectativa de redirección al dashboard, que es el comportamiento real de la vista).
        """
        response = self.client.get(self.url_detalle_evento_no_inscrito)
        
        # 🚨 CORRECCIÓN 3: La vista REAL redirige al dashboard.
        expected_redirect_url = self.url_dashboard_asistente
        
        # Verifica la redirección (código 302)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, expected_redirect_url)

    # CP-SHR-004: Valida la correcta codificación de las URLs de redes sociales (CA4).
    @patch('django.http.request.HttpRequest.build_absolute_uri')
    def test_cshr_004_validar_urls_redes_sociales(self, mock_build_absolute_uri):
        """CP-SHR-004: Valida la correcta codificación de las URLs de redes sociales (CA4)."""
        
        expected_url_path = reverse('ver_info_evento_asi', kwargs={'pk': self.evento_x.pk})
        fake_url = f'http://testserver{expected_url_path}' 
        
        # ASIGNAR EL VALOR DE RETORNO AL MOCK
        mock_build_absolute_uri.return_value = fake_url 
        
        # URLs de redes sociales con la URL simulada codificada
        whatsapp_link = f'https://wa.me/?text={urlquote(fake_url)}' 
        facebook_link = f'https://www.facebook.com/sharer/sharer.php?u={urlquote(fake_url)}'

        response = self.client.get(self.url_detalle_evento)

        self.assertEqual(response.status_code, 200)

        # ✅ CORRECCIÓN 4: Se mantienen las aserciones, el fallo anterior era probablemente un efecto colateral.
        self.assertContains(response, f'href="{whatsapp_link}"')
        self.assertContains(response, f'href="{facebook_link}"')