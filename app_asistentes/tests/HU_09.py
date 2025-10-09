""" Como Compartir la información de los eventos en los que estoy inscrito con mis contactos para 
Motivar a otras personas a asistir a los eventos"""


from urllib.parse import quote_plus
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.hashers import make_password
from unittest.mock import patch, PropertyMock # Se necesita PropertyMock para mocking de .url
from django.contrib.sites.models import Site
from django.contrib.messages import get_messages # Para verificar los mensajes flash

# Importaciones de tus modelos
from app_admin_eventos.models import Evento
from app_asistentes.models import AsistenteEvento
from app_usuarios.models import Usuario, AdministradorEvento, Asistente

# Usamos override_settings para simular la configuración del Site (necesario para URLs absolutas)
@override_settings(SITE_ID=1, ALLOWED_HOSTS=['*'])
class CompartirEventoAsistenteTest(TestCase):

    client = Client()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # 📌 Parche 1: Simula Site.objects.get_current() para build_absolute_uri
        cls.site_patcher = patch.object(Site.objects, 'get_current', 
                                        return_value=Site(domain='testserver', name='test'))
        cls.site_patcher.start()
        
        # 1. Setup Admin y Evento base
        # Usamos update_or_create para crear/obtener el usuario administrador de forma segura
        cls.user_admin, _ = Usuario.objects.update_or_create(
            username='admin_test', defaults={
                'email': 'admin@test.com', 'password': make_password('password'), 
                'rol': Usuario.Roles.ADMIN_EVENTO, 'is_staff': True
            }
        )
        # 📌 CORRECCIÓN: Usar update_or_create para AdministradorEvento para evitar IntegrityError
        cls.admin, _ = AdministradorEvento.objects.update_or_create(
            usuario=cls.user_admin
        ) 
        cls.fecha_proxima = timezone.now().date() + timedelta(days=7)

        # Crear evento con archivos simulados para que no falle al acceder a .url
        cls.evento = Evento.objects.create(
            eve_nombre="Evento Compartible", eve_descripcion="Prueba HU_09",
            eve_estado="Publicado", eve_administrador_fk=cls.admin,
            eve_tienecosto='Sin costo', eve_capacidad=100,
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima,
            eve_imagen=SimpleUploadedFile("img.png", b"file_data"),
            eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf_data")
        )
        
        # 📌 Parche 2: Mock de propiedad 'url' de la imagen (Usa PropertyMock)
        cls.image_url_patcher = patch.object(
            cls.evento.eve_imagen.__class__,
            'url',
            new_callable=PropertyMock,
            return_value='/media/eventos/test_image.png'
        )
        cls.image_url_patcher.start() 
        
        # 📌 Parche 3: Mock de propiedad 'url' de la programación (Usa PropertyMock)
        cls.prog_url_patcher = patch.object(
            cls.evento.eve_programacion.__class__,
            'url',
            new_callable=PropertyMock,
            return_value='/media/programaciones/test_prog.pdf'
        )
        cls.prog_url_patcher.start() 

        # 2. Setup Asistentes (Inscrito vs No Inscrito)
        cls.user_inscrito = Usuario.objects.create_user(
            username='inscrito', email='inscrito@test.com', password='p', rol=Usuario.Roles.ASISTENTE
        )
        cls.asistente_inscrito = Asistente.objects.create(usuario=cls.user_inscrito)
        AsistenteEvento.objects.create(
            asi_eve_evento_fk=cls.evento, asi_eve_asistente_fk=cls.asistente_inscrito, 
            asi_eve_estado='Aprobado', asi_eve_fecha_hora=timezone.now()
        )
        
        cls.user_no_inscrito = Usuario.objects.create_user(
            username='no_inscrito', email='no@test.com', password='p', rol=Usuario.Roles.ASISTENTE
        )
        cls.asistente_no_inscrito = Asistente.objects.create(usuario=cls.user_no_inscrito)

        # 3. URL de la vista (Asegúrate de que 'ver_info_evento_asi' es el nombre correcto de tu URL)
        cls.url = reverse('ver_info_evento_asi', kwargs={'pk': cls.evento.pk})
        

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Detenemos todos los parches.
        cls.site_patcher.stop() 
        cls.image_url_patcher.stop()
        cls.prog_url_patcher.stop()

    def setUp(self):
        # Limpiamos las sesiones/cookies antes de cada test
        self.client.session.clear() 

    # ----------------------------------------------------------------------
    # CP-4.1: Acceso Exitoso y Verificación del Enlace de Compartir
    # ----------------------------------------------------------------------
    def test_cp_4_1_asistente_inscrito_accede_y_genera_enlace_absoluto(self):
        """Valida que el asistente inscrito puede ver el detalle y que el enlace de compartir es absoluto."""
        
        # Simular sesión de asistente inscrito
        session = self.client.session
        session['asistente_id'] = self.asistente_inscrito.pk
        session.save()
        self.client.force_login(self.user_inscrito)
        
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, "CA-4.1 FALLO: El asistente inscrito debería poder acceder.")
        
        # Asumiendo que has implementado la corrección en la vista/plantilla
        # para usar 'ver_detalle_evento'
        expected_absolute_url = f'http://testserver/ver_detalle_evento/{self.evento.pk}' 
        expected_value_attribute = f'value="{expected_absolute_url}"'

        # 1. Verificar el campo de texto (CORRECCIÓN DE SINTAXIS)
        self.assertIn(
            expected_value_attribute,
            response.content.decode('utf-8'),
            "CA-4.2 FALLO: La URL de compartir no contiene el enlace absoluto esperado en el campo de texto."
        )

        # 2. Verificar el enlace de WhatsApp (CORRECCIÓN DE SINTAXIS)
        encoded_url_encontrada = 'http%3A//testserver/ver_detalle_evento/1'

        # 2. Verificar el enlace de WhatsApp
        expected_wa_link_href = f'href="https://wa.me/?text={encoded_url_encontrada}"'
        self.assertIn(
            expected_wa_link_href,
            response.content.decode('utf-8'),
            "CA-4.3 FALLO: El enlace de WhatsApp no contiene la URL absoluta codificada correctamente."
        )

        # 3. Verificar el enlace de Facebook
        expected_fb_link_href = f'href="https://www.facebook.com/sharer/sharer.php?u={encoded_url_encontrada}"'

        self.assertIn(
            expected_fb_link_href,
            response.content.decode('utf-8'),
            "CA-4.4 FALLO: El enlace de Facebook no contiene la URL absoluta codificada correctamente."
        )

    # ----------------------------------------------------------------------
    # CP-4.2: Bloqueo de Acceso a No Inscrito
    # ----------------------------------------------------------------------
    def test_cp_4_2_asistente_no_inscrito_es_redireccionado(self):
        """Valida que un asistente que no está inscrito en el evento es bloqueado y redireccionado."""

        # Simular sesión de asistente NO inscrito
        session = self.client.session
        session['asistente_id'] = self.asistente_no_inscrito.pk
        session.save()
        self.client.force_login(self.user_no_inscrito)
        
        # Usamos follow=True para seguir la redirección final a 'pagina_principal'
        response = self.client.get(self.url, follow=True) 

        # 📌 Se espera 200 al final de la redirección
        self.assertEqual(response.status_code, 200, "CA-4.4 FALLO: Se esperaba 200 después de la redirección a la página principal.")
        
        # Verificar que se redireccionó a la página principal
        self.assertRedirects(response, reverse('dashboard_asistente'), status_code=302, target_status_code=200)

        # Verificar el mensaje de error
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("No tienes permiso para ver este evento." in str(m) for m in messages),
            "CA-4.5 FALLO: No se encontró el mensaje de error de permisos."
        )

    # ----------------------------------------------------------------------
    # CP-4.3: Acceso Denegado a No Asistente/Sin Login
    # ----------------------------------------------------------------------
    def test_cp_4_3_acceso_denegado_sin_login(self):
        """Valida que un usuario sin sesión de asistente no puede acceder."""
        
        self.client.logout() 
        response = self.client.get(self.url)
        
        # 📌 Se espera 302 (Redirección al login por el decorador @asistente_required)
        self.assertEqual(response.status_code, 302, "CA-4.6 FALLO: Se esperaba redirección (302) al login.")
        self.assertTrue(response.url.startswith('/login/'), "CA-4.6 FALLO: No redirigió a la página de inicio de sesión.")