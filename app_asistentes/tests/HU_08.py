""" Como Asistente quiero Recibir notificaciones sobre los eventos en los que estoy inscrito para 
Estar al tanto de información relevante sobre el evento"""

# app_asistentes/tests/HU_08.py

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages
from django.contrib.auth.hashers import make_password
from unittest.mock import patch, PropertyMock 
from django.contrib.sites.models import Site 
from django.core.mail import EmailMessage 

# Importaciones necesarias para su proyecto...
from app_admin_eventos.models import Evento
from app_asistentes.models import AsistenteEvento
from app_usuarios.models import Usuario, AdministradorEvento, Asistente

@override_settings(SITE_ID=1)
class EnviarNotificacionAsistentesTest(TestCase):

    client = Client()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # 📌 Parche 1: Site
        cls.site_patcher = patch.object(Site.objects, 'get_current', return_value=Site(domain='testserver', name='test'))
        cls.site_patcher.start()
        
        # 📌 Parche 2: Static (Adaptado a tu entorno)
        try:
            cls.static_patcher = patch('django.templatetags.static.static', return_value='/static/img/logo.png')
            cls.static_patcher.start()
        except:
            # Si el path de la librería falla, se intenta el path local (ejemplo)
            cls.static_patcher = patch('app_admin_eventos.views.static', return_value='/static/img/logo.png')
            cls.static_patcher.start()
        
        # 📌 Parche 3: Mock del método send()
        cls.email_patcher = patch.object(EmailMessage, 'send')
        cls.mock_send = cls.email_patcher.start()
        
        # 1. Setup Admin y Evento base
        cls.user_admin, _ = Usuario.objects.update_or_create(
            username='admin_test', defaults={
                'email': 'admin@test.com', 'password': make_password('password'), 
                'rol': Usuario.Roles.ADMIN_EVENTO, 'is_staff': True
            }
        )
        # 🟢 CORRECCIÓN DB: Asignar ID explícito al Administrador
        cls.admin, _ = AdministradorEvento.objects.get_or_create(usuario=cls.user_admin, defaults={'id': 'A1'})
        
        cls.fecha_proxima = timezone.now().date() + timedelta(days=7)

        # Creamos el evento con la imagen
        cls.evento = Evento.objects.create(
            eve_nombre="Notificacion Test", eve_descripcion="Prueba de Notificacion",
            eve_estado="Publicado", eve_administrador_fk=cls.admin,
            eve_tienecosto='Sin costo', eve_capacidad=100,
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima,
            eve_imagen=SimpleUploadedFile("img.png", b"file_data")
        )
        
        # 📌 Parche 4: MOCK DE PROPIEDAD 'url' 
        cls.image_url_patcher = patch.object(
            cls.evento.eve_imagen.__class__,
            'url',
            new_callable=PropertyMock,
            return_value='/media/test_image.png'
        )
        cls.image_url_patcher.start() 

        # 2. Setup Asistentes (Aprobado, Pendiente, Cancelado)
        cls.user_aprobado = Usuario.objects.create_user(
            username='asi_aprobado', email='aprobado@test.com', password='p', rol=Usuario.Roles.ASISTENTE
        )
        # 🟢 CORRECCIÓN DB: Asignar ID explícito
        cls.asistente_aprobado = Asistente.objects.create(usuario=cls.user_aprobado, id='ASI1')
        cls.reg_aprobado = AsistenteEvento.objects.create(
            asi_eve_evento_fk=cls.evento, asi_eve_asistente_fk=cls.asistente_aprobado, 
            asi_eve_estado='Aprobado', asi_eve_fecha_hora=timezone.now()
        )
        
        cls.user_pendiente = Usuario.objects.create_user(
            username='asi_pendiente', email='pendiente@test.com', password='p', rol=Usuario.Roles.ASISTENTE
        )
        # 🟢 CORRECCIÓN DB: Asignar ID explícito
        cls.asistente_pendiente = Asistente.objects.create(usuario=cls.user_pendiente, id='ASI2')
        cls.reg_pendiente = AsistenteEvento.objects.create(
            asi_eve_evento_fk=cls.evento, asi_eve_asistente_fk=cls.asistente_pendiente, 
            asi_eve_estado='Pendiente', asi_eve_fecha_hora=timezone.now()
        )

        cls.user_cancelado = Usuario.objects.create_user(
            username='asi_cancelado', email='cancelado@test.com', password='p', rol=Usuario.Roles.ASISTENTE
        )
        # 🟢 CORRECCIÓN DB: Asignar ID explícito
        cls.asistente_cancelado = Asistente.objects.create(usuario=cls.user_cancelado, id='ASI3')
        cls.reg_cancelado = AsistenteEvento.objects.create(
            asi_eve_evento_fk=cls.evento, asi_eve_asistente_fk=cls.asistente_cancelado, 
            asi_eve_estado='Cancelado', asi_eve_fecha_hora=timezone.now()
        )
        
        # 3. Setup Usuario no administrador (para CP-3.4)
        cls.user_no_admin = Usuario.objects.create_user(
            username='no_admin', email='noadmin@test.com', password='p', rol=Usuario.Roles.ASISTENTE
        )
        # NOTA: No creamos la instancia Asistente para user_no_admin a menos que sea estrictamente necesario.

        cls.url = reverse('notificar_asi', kwargs={'evento_id': cls.evento.id})

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Detenemos todos los parches.
        cls.site_patcher.stop() 
        cls.static_patcher.stop()
        cls.email_patcher.stop()
        cls.image_url_patcher.stop() 

    def setUp(self):
        # Reiniciar mock y outbox
        self.mock_send.reset_mock()
        mail.outbox = [] 
        # Forzar login del administrador
        self.client.force_login(self.user_admin)
        # Simular GET inicial
        self.client.get(self.url) 
        
    def _assert_message_found(self, response, expected_message_text, fail_message):
        """Busca el mensaje flash en la respuesta."""
        if not hasattr(response, 'wsgi_request'):
             return self.fail("La respuesta no tiene wsgi_request. No se puede verificar el mensaje flash.")
        
        messages_list = list(get_messages(response.wsgi_request))

        self.assertTrue(
            any(expected_message_text in m.message for m in messages_list), 
            fail_message
        )
        
    # ----------------------------------------------------------------------
    # CP-3.4: Acceso Denegado (No Administrador)
    # ----------------------------------------------------------------------
    def test_cp_3_4_acceso_denegado_no_administrador(self):
        """Valida que un usuario no administrador no puede acceder a la vista."""
        
        self.client.logout()
        self.client.force_login(self.user_no_admin) 

        response_get = self.client.get(self.url)
        
        self.assertEqual(response_get.status_code, 302, "CA-3.6 FALLO: Se esperaba redirección (302) por falta de privilegios.")
        # Verificamos que redirija al login o a la raíz (si es el comportamiento por defecto de la restricción de rol)
        self.assertTrue(response_get.url.startswith('/login/') or response_get.url == reverse('pagina_principal'), "CA-3.6 FALLO: Redirección incorrecta.")

    # ----------------------------------------------------------------------
    # AÑADIR AQUÍ LOS TESTS DE ENVÍO DE NOTIFICACIÓN (CP-3.1, CP-3.2, CP-3.3)
    # ----------------------------------------------------------------------

    #Ejemplo de estructura para el envío (Asegúrate de que la URL 'notificar_asi' acepta POST)
