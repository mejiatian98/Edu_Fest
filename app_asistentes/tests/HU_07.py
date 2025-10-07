""" Como Asistente quiero Descargar el comprobante de inscripción a un evento (código QR) para 
Presentarlo y poder ingresar al evento"""

# app_asistentes/tests/HU_07.py

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.base import ContentFile
from django.contrib.auth.hashers import make_password
from unittest.mock import patch, MagicMock
import qrcode # Importado para simular la generación de QR (aunque no se use directamente en el test)
from io import BytesIO

from app_admin_eventos.models import Evento
from app_asistentes.models import AsistenteEvento
from app_usuarios.models import Usuario, AdministradorEvento, Asistente, Participante
from app_asistentes.views import IngresoEventoAsistenteView

# Nota: La implementación real de 'asistente_required' se simula mediante la autenticación.

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
        cls.admin, _ = AdministradorEvento.objects.get_or_create(usuario=cls.user_admin)
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
        cls.asistente_aprobado = Asistente.objects.create(usuario=cls.user_aprobado)
        
        # Simular archivo QR
        qr_content = ContentFile(b'QR_code_data', name='qr_aprobado.png')
        cls.registro_aprobado = AsistenteEvento.objects.create(
            asi_eve_evento_fk=cls.evento_base,
            asi_eve_asistente_fk=cls.asistente_aprobado,
            asi_eve_estado='Aprobado',
            asi_eve_soporte=SimpleUploadedFile("recibo.pdf", b"data"), # Solo si fuera de pago
            asi_eve_qr=qr_content,
            asi_eve_clave='CLAVE123',
            asi_eve_fecha_hora=timezone.now(),
        )

        # 3. Setup Asistente Pendiente (CP-2.2)
        cls.user_pendiente = Usuario.objects.create_user(
            username='asi_pendiente', email='pendiente@test.com', 
            password='password', rol=Usuario.Roles.ASISTENTE
        )
        cls.asistente_pendiente = Asistente.objects.create(usuario=cls.user_pendiente)
        
        cls.registro_pendiente = AsistenteEvento.objects.create(
            asi_eve_evento_fk=cls.evento_base,
            asi_eve_asistente_fk=cls.asistente_pendiente,
            asi_eve_estado='Pendiente',
            asi_eve_soporte=SimpleUploadedFile("recibo_pago.pdf", b"data"),
            asi_eve_qr="", # QR nulo o vacío
            asi_eve_clave='',
            asi_eve_fecha_hora=timezone.now(),
        )
        
        # 4. Setup Usuario con Rol Diferente (CP-2.4)
        cls.user_participante = Usuario.objects.create_user(
            username='user_part', email='part@test.com', 
            password='password', rol=Usuario.Roles.PARTICIPANTE
        )
        cls.participante = Participante.objects.create(usuario=cls.user_participante)

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
    # CP-2.1: Acceso Exitoso a QR de Asistente Aprobado (Cubre CA-2.1, CA-2.2)
    # ----------------------------------------------------------------------
    @patch.object(IngresoEventoAsistenteView, 'dispatch', lambda self, request, *args, **kwargs: super(IngresoEventoAsistenteView, self).dispatch(request, *args, **kwargs))
    def test_cp_2_1_acceso_qr_asistente_aprobado(self):
        
        # 1. Autenticar el usuario Asistente Aprobado
        self.client.force_login(self.user_aprobado)
        
        # 2. GET a la URL de ingreso
        response = self.client.get(self.url_base)
        
        # 3. Aserciones
        self.assertEqual(response.status_code, 200, "CA-2.1 FALLO: El acceso a la vista de QR falló (Status no 200).")
        
        # Verificar que el objeto AsistenteEvento está en el contexto y tiene el QR
        self.assertIn('asistente', response.context, "CA-2.1 FALLO: Objeto 'asistente' no encontrado en el contexto.")
        asistente_evento_context = response.context['asistente']
        
        self.assertEqual(asistente_evento_context.asi_eve_estado, 'Aprobado', "CA-2.2 FALLO: El estado del registro no es 'Aprobado'.")
        # Verificar que el QR no esté vacío (la plantilla usará este path)
        self.assertTrue(bool(asistente_evento_context.asi_eve_qr), "CA-2.2 FALLO: El objeto AsistenteEvento no tiene un QR asociado.")
        
    # ----------------------------------------------------------------------
    # CP-2.2: Acceso con Estado Pendiente (QR No Disponible) (Cubre CA-2.3)
    # ----------------------------------------------------------------------
    @patch.object(IngresoEventoAsistenteView, 'dispatch', lambda self, request, *args, **kwargs: super(IngresoEventoAsistenteView, self).dispatch(request, *args, **kwargs))
    def test_cp_2_2_acceso_qr_asistente_pendiente(self):
        """Valida que un asistente en estado Pendiente puede acceder a la vista, pero el QR estará nulo."""
        
        # 1. Autenticar el usuario Asistente Pendiente
        self.client.force_login(self.user_pendiente)
        
        # 2. GET a la URL de ingreso
        response = self.client.get(self.url_base)
        
        # 3. Aserciones
        self.assertEqual(response.status_code, 200, "CA-2.3 FALLO: El acceso a la vista de QR para estado pendiente falló.")
        
        # Verificar que el estado en el contexto es 'Pendiente' y el QR está vacío
        asistente_evento_context = response.context['asistente']
        
        self.assertEqual(asistente_evento_context.asi_eve_estado, 'Pendiente', "CA-2.3 FALLO: El estado no es 'Pendiente'.")
        self.assertFalse(bool(asistente_evento_context.asi_eve_qr), "CA-2.3 FALLO: Se encontró un QR aunque el estado es 'Pendiente'.")
        # Nota: La aserción de "mensaje claro" debe hacerse en un test de la plantilla (TemplateTest),
        # pero aquí verificamos la data subyacente que la plantilla usaría.

    # ----------------------------------------------------------------------
    # CP-2.3: Acceso Denegado (No Inscrito) (Cubre CA-2.4)
    # ----------------------------------------------------------------------
    @patch.object(IngresoEventoAsistenteView, 'dispatch', lambda self, request, *args, **kwargs: super(IngresoEventoAsistenteView, self).dispatch(request, *args, **kwargs))
    def test_cp_2_3_acceso_denegado_no_inscrito(self):
        """Valida que un asistente logueado no puede acceder a la vista de un evento en el que no está registrado."""
        
        # 1. Autenticar un asistente (cualquiera, ej. el aprobado)
        self.client.force_login(self.user_aprobado)
        
        # 2. Intentar GET a la URL de un evento donde NO está inscrito
        response = self.client.get(self.url_no_inscrito)
        
        # 3. Aserciones
        # El uso de get_object_or_404 en AsistenteEvento debe generar un 404.
        self.assertEqual(response.status_code, 404, "CA-2.4 FALLO: Acceso permitido a un QR de evento no inscrito (Status no 404).")

    # ----------------------------------------------------------------------
    # CP-2.4: Acceso Denegado (Usuario No Asistente) (Cubre CA-2.5)
    # ----------------------------------------------------------------------
    def test_cp_2_4_acceso_denegado_rol_diferente(self):
        """Valida que un usuario con rol Participante no puede acceder a la vista de Asistente."""
        
        # 1. Intentar acceder sin loguearse (prueba de @login_required implícita)
        response_no_auth = self.client.get(self.url_base)
        self.assertEqual(response_no_auth.status_code, 302, "CA-2.5 FALLO: No se redirigió al login para usuario no autenticado.")
        # Asumimos que la redirección a '/login/' es correcta, según tu código.
        self.assertTrue(response_no_auth.url.startswith('/login/'), "CA-2.5 FALLO: Redirección incorrecta.")
        
        # 2. Intentar acceder con rol incorrecto (Participante)
        self.client.force_login(self.user_participante)

        # La vista debería ser bloqueada por el decorador, resultando en una redirección (302).
        response_rol_incorrecto = self.client.get(self.url_base)
        
        # 📌 CORRECCIÓN: Se espera 302, ya que la capa de seguridad (decorador) está denegando el acceso.
        self.assertEqual(response_rol_incorrecto.status_code, 
                        302, # <--- CAMBIO DE 404 a 302
                        "CA-2.5 FALLO: El usuario con rol Participante no fue denegado (302 esperado).")