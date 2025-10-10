""" Como Asistente quiero Descargar el comprobante de inscripción a un evento (código QR) para 
Presentarlo y poder ingresar al evento"""

# app_asistentes/tests/HU_07.py (Código corregido para solucionar IntegrityError)

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.base import ContentFile
from unittest.mock import patch, MagicMock
from io import BytesIO

# Importaciones de Modelos (Asumidas correctas)
from app_admin_eventos.models import Evento
from app_asistentes.models import AsistenteEvento
from app_usuarios.models import Usuario, AdministradorEvento, Asistente, Participante
from app_asistentes.views import IngresoEventoAsistenteView

@patch('app_asistentes.views.asistente_required', lambda f: f)
class IngresoEventoAsistenteTest(TestCase):

    client = Client()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # 1. Setup Admin y Evento base
        cls.user_admin = Usuario.objects.create_user(
            username='admin_test', email='admin@test.com', 
            password='password', rol=Usuario.Roles.ADMIN_EVENTO, is_staff=True
        )
        # Asignar ID explícito si el campo ID no es auto_increment
        cls.admin, _ = AdministradorEvento.objects.get_or_create(usuario=cls.user_admin, defaults={'id': 'AD1'})
        
        cls.fecha_proxima = timezone.now().date() + timedelta(days=7)

        cls.evento_base = Evento.objects.create(
            eve_nombre="Conferencia QR", eve_descripcion="Prueba de QR",
            eve_estado="Publicado", eve_administrador_fk=cls.admin,
            eve_tienecosto='Sin costo', eve_capacidad=100,
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima,
            eve_ciudad='Ciudad', eve_lugar='Lugar', 
            eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf_data"), 
            eve_imagen=SimpleUploadedFile("img.png", b"file_data")
        )
        
        # 2. Setup Asistente Aprobado (CP-2.1)
        cls.user_aprobado = Usuario.objects.create_user(
            username='asi_aprobado', email='aprobado@test.com', 
            password='password', rol=Usuario.Roles.ASISTENTE
        )
        # 🔴 CORRECCIÓN CLAVE: Asignar ID explícito al Asistente
        cls.asistente_aprobado = Asistente.objects.create(usuario=cls.user_aprobado, id='AS1')
        
        # Simular archivo QR
        qr_content = ContentFile(b'QR_code_data', name='qr_aprobado.png')
        cls.registro_aprobado = AsistenteEvento.objects.create(
            asi_eve_evento_fk=cls.evento_base,
            asi_eve_asistente_fk=cls.asistente_aprobado,
            asi_eve_estado='Aprobado',
            asi_eve_soporte=SimpleUploadedFile("recibo.pdf", b"data"), 
            asi_eve_qr=qr_content,
            asi_eve_clave='CLAVE123',
            asi_eve_fecha_hora=timezone.now(),
        )

        # 3. Setup Asistente Pendiente (CP-2.2)
        cls.user_pendiente = Usuario.objects.create_user(
            username='asi_pendiente', email='pendiente@test.com', 
            password='password', rol=Usuario.Roles.ASISTENTE
        )
        # 🔴 CORRECCIÓN CLAVE: Asignar ID explícito al Asistente
        cls.asistente_pendiente = Asistente.objects.create(usuario=cls.user_pendiente, id='AS2')
        
        cls.registro_pendiente = AsistenteEvento.objects.create(
            asi_eve_evento_fk=cls.evento_base,
            asi_eve_asistente_fk=cls.asistente_pendiente,
            asi_eve_estado='Pendiente',
            asi_eve_soporte=SimpleUploadedFile("recibo_pago.pdf", b"data"),
            asi_eve_qr="", 
            asi_eve_clave='',
            asi_eve_fecha_hora=timezone.now(),
        )
        
        # 4. Setup Usuario con Rol Diferente (CP-2.4)
        cls.user_participante = Usuario.objects.create_user(
            username='user_part', email='part@test.com', 
            password='password', rol=Usuario.Roles.PARTICIPANTE
        )
        # 🔴 CORRECCIÓN CLAVE: Asignar ID explícito al Participante
        cls.participante = Participante.objects.create(usuario=cls.user_participante, id='PA1')

        # 5. URL para la prueba
        cls.url_base = reverse('ingreso_evento_asi', kwargs={'pk': cls.evento_base.pk})
        
        # 6. Setup evento_no_inscrito (Para CP-2.3)
        cls.evento_no_inscrito = Evento.objects.create(
            eve_nombre="Evento Ajeno", eve_descripcion="No inscrito",
            eve_estado="Publicado", eve_administrador_fk=cls.admin,
            eve_tienecosto='Sin costo', eve_capacidad=10,
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima,
            eve_ciudad='Ciudad', eve_lugar='Lugar', 
            eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf_data"), 
            eve_imagen=SimpleUploadedFile("img.png", b"file_data")
        )
        cls.url_no_inscrito = reverse('ingreso_evento_asi', kwargs={'pk': cls.evento_no_inscrito.pk})


    # ----------------------------------------------------------------------
    # CP-2.1: Acceso Exitoso a QR de Asistente Aprobado 
    # ----------------------------------------------------------------------
    @patch.object(IngresoEventoAsistenteView, 'dispatch', lambda self, request, *args, **kwargs: super(IngresoEventoAsistenteView, self).dispatch(request, *args, **kwargs))
    def test_cp_2_1_acceso_qr_asistente_aprobado(self):
        self.client.force_login(self.user_aprobado)
        response = self.client.get(self.url_base)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('asistente', response.context)
        asistente_evento_context = response.context['asistente']
        
        self.assertEqual(asistente_evento_context.asi_eve_estado, 'Aprobado')
        self.assertTrue(bool(asistente_evento_context.asi_eve_qr))
        
    # ----------------------------------------------------------------------
    # CP-2.2: Acceso con Estado Pendiente (QR No Disponible)
    # ----------------------------------------------------------------------
    @patch.object(IngresoEventoAsistenteView, 'dispatch', lambda self, request, *args, **kwargs: super(IngresoEventoAsistenteView, self).dispatch(request, *args, **kwargs))
    def test_cp_2_2_acceso_qr_asistente_pendiente(self):
        self.client.force_login(self.user_pendiente)
        response = self.client.get(self.url_base)
        
        self.assertEqual(response.status_code, 200)
        asistente_evento_context = response.context['asistente']
        
        self.assertEqual(asistente_evento_context.asi_eve_estado, 'Pendiente')
        self.assertFalse(bool(asistente_evento_context.asi_eve_qr))

    # ----------------------------------------------------------------------
    # CP-2.3: Acceso Denegado (No Inscrito) 
    # ----------------------------------------------------------------------
    @patch.object(IngresoEventoAsistenteView, 'dispatch', lambda self, request, *args, **kwargs: super(IngresoEventoAsistenteView, self).dispatch(request, *args, **kwargs))
    def test_cp_2_3_acceso_denegado_no_inscrito(self):
        self.client.force_login(self.user_aprobado)
        response = self.client.get(self.url_no_inscrito)
        
        # Esperamos un 404 porque no hay registro AsistenteEvento para este usuario/evento
        self.assertEqual(response.status_code, 404)

    # ----------------------------------------------------------------------
    # CP-2.4: Acceso Denegado (Usuario No Asistente) 
    # ----------------------------------------------------------------------
    def test_cp_2_4_acceso_denegado_rol_diferente(self):
        # 1. Acceso sin autenticar
        response_no_auth = self.client.get(self.url_base)
        self.assertEqual(response_no_auth.status_code, 302)
        
        # 2. Acceso con rol incorrecto (Participante)
        self.client.force_login(self.user_participante)

        # Se espera 302 (Redirección por el decorador 'asistente_required')
        response_rol_incorrecto = self.client.get(self.url_base)
        
        self.assertEqual(response_rol_incorrecto.status_code, 302)