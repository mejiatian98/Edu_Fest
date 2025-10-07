""" Como visitante web (asistente) Anexar soporte(s) del pago requerido para la asistencia a eventos con cobro de ingreso para 
Asegurar mi asistencia y cupo en el evento"""


# app_asistentes/tests/HU_06.py

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.hashers import make_password
# Se necesitan estos imports para simular el ambiente de la vista
import random
import string
from io import BytesIO
from django.core.files.base import ContentFile
from app_admin_eventos.models import Evento
from app_asistentes.models import AsistenteEvento
from app_usuarios.models import Usuario, AdministradorEvento, Asistente

# IMPORTANTE: Asegúrate de que tu AsistenteForm valide los campos de archivo (MIME types).
# Dado que la validación de formato/tamaño no está en la vista, sino en el Formulario,
# el CP-1.3 puede requerir un manejo específico si el Formulario no está adjunto. 
# Asumiremos la validación por defecto o una excepción si Django la lanza.

class AsistentePagoSoporteTest(TestCase):
    
    # Cliente de prueba
    client = Client()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Setup robusto de Admin (PK fijo para evitar IntegrityError)
        ADMIN_USER_ID = 9999
        cls.user_admin, _ = Usuario.objects.update_or_create(
            pk=ADMIN_USER_ID,
            defaults={'username': 'admin_test', 'email': 'admin@test.com', 
                      'password': make_password('password'), 
                      'rol': Usuario.Roles.ADMIN_EVENTO, 'is_staff': True}
        )
        cls.admin, _ = AdministradorEvento.objects.update_or_create(usuario=cls.user_admin)
        cls.fecha_proxima = timezone.now().date() + timedelta(days=7)

        # Evento 1: De Pago (Capacidad 100)
        cls.evento_pago = Evento.objects.create(
            eve_nombre="Conferencia de Pago", eve_descripcion="Costo 100",
            eve_estado="Publicado", eve_administrador_fk=cls.admin,
            eve_tienecosto='De pago', eve_capacidad=100,
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima,
            eve_ciudad='Ciudad', eve_lugar='Lugar', 
            eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf_data"), 
            eve_imagen=SimpleUploadedFile("img.png", b"file_data")
        )

        # Evento 2: Sin Costo (Capacidad 100)
        cls.evento_gratis = Evento.objects.create(
            eve_nombre="Conferencia Gratuita", eve_descripcion="Sin Costo",
            eve_estado="Publicado", eve_administrador_fk=cls.admin,
            eve_tienecosto='Sin costo', eve_capacidad=100,
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima,
            eve_ciudad='Ciudad', eve_lugar='Lugar', 
            eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf_data"), 
            eve_imagen=SimpleUploadedFile("img.png", b"file_data")
        )
        
        # Evento 3: Capacidad Agotada (Para validar el CP de la vista)
        cls.evento_lleno = Evento.objects.create(
            eve_nombre="Evento Lleno", eve_descripcion="Cupos 0",
            eve_estado="Publicado", eve_administrador_fk=cls.admin,
            eve_tienecosto='Sin costo', eve_capacidad=0, 
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima,
            eve_ciudad='Ciudad', eve_lugar='Lugar', 
            eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf_data"), 
            eve_imagen=SimpleUploadedFile("img.png", b"file_data")
        )
        
        # Datos base del formulario (Usuario nuevo)
        cls.asistente_data = {
            'id': '100000001',
            'username': 'asistente.base',
            'email': 'asistente.base@test.com',
            'telefono': '3001234567',
            'first_name': 'Juan',
            'last_name': 'Perez',
        }
        cls.url_pago = reverse('crear_asistente', kwargs={'pk': cls.evento_pago.pk})
        cls.url_gratis = reverse('crear_asistente', kwargs={'pk': cls.evento_gratis.pk})
        cls.url_lleno = reverse('crear_asistente', kwargs={'pk': cls.evento_lleno.pk})
        
        # Archivos de prueba
        cls.pdf_valido = SimpleUploadedFile("soporte.pdf", b"pdf content", content_type="application/pdf")
        cls.archivo_invalido = SimpleUploadedFile("script.sh", b"bash script", content_type="text/x-shellscript")
        
        # Simular envio de email para evitar errores en pruebas
        cls.mail_patcher = cls.patch_email_backend()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if hasattr(cls, 'mail_patcher') and cls.mail_patcher:
            cls.mail_patcher.stop()

    def setUp(self):
        # Reiniciar el cliente y el mock de email antes de cada prueba
        self.client = Client()
        self.mail_patcher.start()

    def tearDown(self):
        self.mail_patcher.stop()

    @staticmethod
    def patch_email_backend():
        from unittest.mock import patch
        return patch('django.core.mail.backends.locmem.EmailBackend')


    # ----------------------------------------------------------------------
    # CP-1.1: Registro Exitoso Evento Pago con Soporte Válido (Cubre CA-1.1, CA-1.2, CA-1.4)
    # ----------------------------------------------------------------------
    def test_cp_1_1_registro_pago_con_soporte_valido(self):
        """Valida que un asistente adjunta soporte, el estado es 'Pendiente' y se resta la capacidad."""
        
        data = self.asistente_data.copy()
        data['asi_eve_soporte'] = self.pdf_valido
        data['username'] = 'asistente_pago_ok'
        data['id'] = '100000006' 
        data['email'] = 'asistente_pago_ok@test.com'
        
        capacidad_inicial = self.evento_pago.eve_capacidad
        
        response = self.client.post(self.url_pago, data, follow=True)
        
        # 1. Aserciones de la Respuesta
        self.assertEqual(response.status_code, 200, "CA-1.1 FALLO: La solicitud POST no fue exitosa (Status 200).")
        # El mensaje de la vista es f"La preinscripción fue exitosa al evento \"{evento.eve_nombre}\"."
        self.assertContains(response, "La preinscripción fue exitosa al evento", status_code=200, 
                            msg_prefix="CA-1.1 FALLO: No se mostró el mensaje de éxito/pendiente.")

        # 2. Aserciones del Modelo
        asistente_evento = AsistenteEvento.objects.filter(
            asi_eve_evento_fk=self.evento_pago, 
            asi_eve_asistente_fk__usuario__username='asistente_pago_ok'
        ).first()

        self.assertIsNotNone(asistente_evento, "CA-1.1 FALLO: No se creó el registro AsistenteEvento.")
        self.assertEqual(asistente_evento.asi_eve_estado, 'Pendiente', "CA-1.2 FALLO: El estado no es 'Pendiente'.")
        self.assertTrue(bool(asistente_evento.asi_eve_soporte), "CA-1.4 FALLO: El campo asi_eve_soporte está vacío/nulo.")
        
        # 3. Verificar reducción de capacidad
        self.evento_pago.refresh_from_db()
        self.assertEqual(self.evento_pago.eve_capacidad, capacidad_inicial - 1, "CA-1.1 FALLO: La capacidad del evento no se redujo.")

    # ----------------------------------------------------------------------
    # CP-1.2: Registro Fallido sin Adjuntar Soporte (Evento Pago) (Cubre CA-1.3)
    # ----------------------------------------------------------------------
    def test_cp_1_2_registro_pago_sin_soporte(self):
        """Valida que la inscripción a un evento de pago sin soporte es rechazada por la lógica de la vista."""
        
        data = self.asistente_data.copy()
        # NO se adjunta 'asi_eve_soporte'
        data['username'] = 'asistente_sin_soporte'
        data['id'] = '100000007' 
        data['email'] = 'asistente_sin@test.com'

        response = self.client.post(self.url_pago, data, follow=True)
        
        # 1. Aserciones de la Respuesta
        self.assertEqual(response.status_code, 200, "CA-1.3 FALLO: No se devolvió la página de formulario con error (Status 200).")
        # Mensaje de error de la vista: "Debe cargar el comprobante de pago para este evento."
        self.assertContains(response, "Debe cargar el comprobante de pago para este evento.", status_code=200, 
                            msg_prefix="CA-1.3 FALLO: No se mostró el mensaje de soporte obligatorio.")

        # 2. Aserciones del Modelo
        self.assertFalse(AsistenteEvento.objects.filter(asi_eve_asistente_fk__usuario__username='asistente_sin_soporte').exists(),
                         "CA-1.3 FALLO: Se creó un registro AsistenteEvento sin el soporte requerido.")

    # ----------------------------------------------------------------------
    # CP-1.3: Registro Fallido con Capacidad Agotada (Implementación de la vista)
    # ----------------------------------------------------------------------
    def test_cp_1_3_registro_fallido_capacidad_agotada_vista(self):
        """Valida que el registro falla si eve_capacidad es 0 según la lógica de la vista."""
        
        # El evento_lleno tiene eve_capacidad=0
        data = self.asistente_data.copy()
        data['username'] = 'asistente_lleno'
        data['id'] = '100000008' 
        data['email'] = 'asistente_lleno@test.com'

        response = self.client.post(self.url_lleno, data, follow=True)
        
        # 1. Aserciones de la Respuesta
        self.assertEqual(response.status_code, 200, "CA-1.3 FALLO: La vista no regresó la página de registro (Status 200).")
        # Mensaje de error de la vista: "No hay más cupos disponibles para este evento."
        self.assertContains(response, "No hay más cupos disponibles para este evento.", status_code=200, 
                            msg_prefix="CA-1.3 FALLO: No se mostró el mensaje de cupos agotados.")

        # 2. Aserciones del Modelo
        self.assertFalse(AsistenteEvento.objects.filter(asi_eve_evento_fk=self.evento_lleno).exists(),
                         "CA-1.3 FALLO: Se creó un registro AsistenteEvento a pesar de la capacidad agotada.")

    # ----------------------------------------------------------------------
    # CP-1.4: Registro Exitoso Evento Gratuito (Sin Soporte Requerido) (Cubre CA-1.5)
    # ----------------------------------------------------------------------
    def test_cp_1_4_registro_gratuito_aprobado_automatico(self):
        """Valida que la inscripción a un evento gratuito no requiere soporte y es 'Aprobado' automáticamente."""
        
        data = self.asistente_data.copy()
        # NO se incluye asi_eve_soporte en la data
        data['username'] = 'asistente_gratis_ok'
        data['id'] = '100000009' 
        data['email'] = 'asistente_gratis_ok@test.com'
        
        capacidad_inicial = self.evento_gratis.eve_capacidad

        response = self.client.post(self.url_gratis, data, follow=True)
        
        # 1. Aserciones de la Respuesta
        self.assertEqual(response.status_code, 200, "CA-1.5 FALLO: La solicitud POST no devolvió 200/redirigió correctamente.")
        self.assertContains(response, "La preinscripción fue exitosa al evento", status_code=200, 
                            msg_prefix="CA-1.5 FALLO: No se mostró el mensaje de éxito/aprobación.")

        # 2. Aserciones del Modelo
        asistente_evento = AsistenteEvento.objects.filter(
            asi_eve_evento_fk=self.evento_gratis, 
            asi_eve_asistente_fk__usuario__username='asistente_gratis_ok'
        ).first()

        self.assertIsNotNone(asistente_evento, "CA-1.5 FALLO: No se creó el registro AsistenteEvento.")
        self.assertEqual(asistente_evento.asi_eve_estado, 'Aprobado', "CA-1.5 FALLO: El estado no es 'Aprobado'.")
        self.assertFalse(bool(asistente_evento.asi_eve_soporte), "CA-1.5 FALLO: El campo asi_eve_soporte no está vacío para evento gratuito.")

        # 3. Verificar reducción de capacidad
        self.evento_gratis.refresh_from_db()
        self.assertEqual(self.evento_gratis.eve_capacidad, capacidad_inicial - 1, "CA-1.5 FALLO: La capacidad del evento no se redujo.")