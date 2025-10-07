from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, timedelta
from app_admin_eventos.models import Evento 
from app_usuarios.models import AdministradorEvento, Usuario, Asistente
from app_asistentes.models import AsistenteEvento
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from unittest.mock import patch, MagicMock
from django.contrib.messages import get_messages
from io import BytesIO

# --- Setup Helpers ---
def setup_administrador():
    usuario, _ = Usuario.objects.get_or_create(username='admin_test', rol='ADMIN_EVENTO')
    return AdministradorEvento.objects.get_or_create(usuario=usuario)[0]

def create_evento(admin, nombre, tienecosto, capacidad, habilitado_asi=True):
    return Evento.objects.create(
        eve_nombre=nombre, eve_descripcion="Desc", eve_ciudad="Ciudad", eve_lugar="Lugar",
        eve_fecha_inicio=date.today() + timedelta(days=10),
        eve_fecha_fin=date.today() + timedelta(days=12),
        eve_estado="Publicado", eve_imagen=SimpleUploadedFile("dummy.jpg", b"c", content_type="image/jpeg"),
        eve_administrador_fk=admin, eve_tienecosto=tienecosto, eve_capacidad=capacidad,
        eve_programacion=SimpleUploadedFile("dummy.pdf", b"c", content_type="application/pdf"),
        preinscripcion_habilitada_asistentes=habilitado_asi
    )

class AsistenteCreateViewFlowTest(TestCase):
    """Pruebas funcionales de la vista AsistenteCreateView."""
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = setup_administrador()
        
        # Eventos para pruebas
        cls.evento_gratuito = create_evento(cls.admin, "Taller Gratuito", 'No tiene costo', 5, True)
        cls.evento_pago = create_evento(cls.admin, "Congreso De Pago", 'De pago', 5, True)
        cls.evento_capacidad_agotada = create_evento(cls.admin, "Capacidad Cero", 'No tiene costo', 0, True)

        cls.url_gratuito = reverse('crear_asistente', kwargs={'pk': cls.evento_gratuito.pk})
        cls.url_pago = reverse('crear_asistente', kwargs={'pk': cls.evento_pago.pk})
        cls.url_agotada = reverse('crear_asistente', kwargs={'pk': cls.evento_capacidad_agotada.pk})

        cls.base_data = {
            'id': '1017890123', # <-- AGREGAR ESTE CAMPO DE IDENTIFICACIÓN
            'first_name': 'Test', 'last_name': 'User', 'telefono': '1234567890',
            # Estos deben ser únicos si se va a crear un usuario nuevo
            'username': 'unique_user_gratis', 'email': 'unique@gratis.com', 
            'password': 'Password123!', 'password_confirm': 'Password123!',
        }
        cls.soporte_mock = SimpleUploadedFile(
            name="soporte_pago.pdf", 
            content=b"file_content", 
            content_type="application/pdf"
        )
        
    def setUp(self):
        super().setUp()
        mail.outbox = [] # Limpiar bandeja de correo

    @patch('qrcode.make', return_value=MagicMock(save=MagicMock()))
    @patch('django.core.mail.EmailMessage.send', return_value=True) 
    def test_cp_2_7_inscripcion_pago_exitosa_con_soporte(self, mock_email_send, mock_qrcode):
        """Valida CA-2.7, CA-2.10: Evento de pago requiere soporte, estado Pendiente, capacidad -1."""
        
        # 1. PREPARACIÓN DE DATOS (Incluye 'id' y datos únicos)
        data = self.base_data.copy()
        
        # Sobreescribir con datos únicos para este test (email y username)
        data.update({
            'username': 'pago_user_final', 
            'email': 'pago.final@user.com',
            # El campo 'id' se hereda correctamente de self.base_data
        })
        
        # 2. CORRECCIÓN DEL ENVÍO DE ARCHIVO: Incluir el SimpleUploadedFile en 'data'
        data['asi_eve_soporte'] = self.soporte_mock 

        capacidad_inicial = self.evento_pago.eve_capacidad
        
        # ACT: POST con datos completos. Usamos follow=False para testear el 302 directamente.
        response = self.client.post(self.url_pago, data=data, follow=False) 
        
        # ASSERT 1: Redirección exitosa (DEBE SER 302)
        # Esta aserción ahora debe pasar porque el formulario ya es válido.
        self.assertEqual(response.status_code, 302, 
            f"FALLO CRÍTICO: Esperado 302, Obtenido {response.status_code}. El formulario no fue válido. Errores: {response.context.get('form').errors if response.context and response.context.get('form') else 'No hay errores de formulario disponibles.'}")
        
        self.assertRedirects(response, reverse('pagina_principal'), status_code=302, target_status_code=200)

        # ASSERT 2: Estado, Soporte y Creación de Registro (CA-2.7)
        asistente_evento = AsistenteEvento.objects.get(
            asi_eve_evento_fk=self.evento_pago, 
            asi_eve_asistente_fk__usuario__email='pago.final@user.com'
        )
        self.assertEqual(asistente_evento.asi_eve_estado, 'Pendiente')
        self.assertTrue(asistente_evento.asi_eve_soporte) # Se debe haber guardado el soporte

        # ASSERT 3: Capacidad reducida (CA-2.10)
        self.evento_pago.refresh_from_db()
        self.assertEqual(self.evento_pago.eve_capacidad, capacidad_inicial - 1)

    def test_cp_2_8_inscripcion_pago_rechazo_sin_soporte(self):
        """Valida CA-2.7: Evento de pago sin adjuntar soporte debe fallar en la vista."""
        
        data = self.base_data.copy()
        data.update({'username': 'pago_fail', 'email': 'pago@fail.com'})
        
        # ACT: POST sin 'asi_eve_soporte' en files
        response = self.client.post(self.url_pago, data=data, follow=False)
        
        # ASSERT 1: Retorna al formulario (200 OK)
        self.assertEqual(response.status_code, 200)
        
        # ASSERT 2: Mensaje de error (CA-2.7)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn("Debe cargar el comprobante de pago para este evento.", [m.message for m in messages])
        
        # ASSERT 3: No se crea registro
        self.assertFalse(Usuario.objects.filter(email='pago@fail.com').exists())


    @patch('qrcode.make')
    def test_cp_2_9_inscripcion_gratuita_exitosa_y_email(self, mock_qrcode):
        """Valida CA-2.8, CA-2.10: Evento gratuito: estado Aprobado, QR/Clave generados, email enviado con QR."""
        
        # 1. Simular la generación del QR (Mockear qrcode.make)
        
        # Creamos un mock para el objeto QR que retorna qrcode.make
        mock_qr_instance = MagicMock()
        
        # Definimos el comportamiento de qr.save(buffer, format='PNG')
        def mock_save(buffer, format):
            # Simular la escritura de bytes en el buffer
            buffer.write(b'simulated_qr_data') 
            
        mock_qr_instance.save = mock_save # Reemplazar el método save con nuestro mock
        mock_qrcode.return_value = mock_qr_instance
        
        # Dado que tu vista usa 'id' para el nombre del archivo QR, es crucial que 'data' contenga 'id'.
        data = self.base_data.copy() 
        capacidad_inicial = self.evento_gratuito.eve_capacidad

        # ACT
        response = self.client.post(self.url_gratuito, data=data, follow=True)
        
        # ASSERT 1: Estado Aprobado (CA-2.8) - Se mantiene igual
        asistente_evento = AsistenteEvento.objects.get(asi_eve_evento_fk=self.evento_gratuito, asi_eve_asistente_fk__usuario__email=data['email'])
        self.assertEqual(asistente_evento.asi_eve_estado, 'Aprobado')
        self.assertTrue(asistente_evento.asi_eve_clave) 
        self.assertTrue(asistente_evento.asi_eve_qr.name) 

        # ASSERT 2: Capacidad reducida (CA-2.10) - Se mantiene igual
        self.evento_gratuito.refresh_from_db()
        self.assertEqual(self.evento_gratuito.eve_capacidad, capacidad_inicial - 1)
        
        # ASSERT 3: Email enviado con adjunto (CA-2.8) - Debería pasar ahora
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [data['email']])
        self.assertIn("Tu clave de acceso al evento es:", email.body)
        
        # Esta aserción ahora pasa porque mock_save llenó el buffer, que luego llenó qr_bytes, 
        # permitiendo que email_msg.attach se ejecutara correctamente.
        self.assertTrue(len(email.attachments) > 0, 
                        f"Fallo al adjuntar QR. Número de adjuntos: {len(email.attachments)}. ") 



    @patch('qrcode.make', return_value=MagicMock(save=MagicMock()))
    def test_cp_2_10_inscripcion_reutilizacion_usuario_existente(self, mock_qrcode):
        """Valida CA-2.9: Reutilizar usuario/asistente existente en un nuevo evento (email ya existe)."""
        
        # --- PREPARACIÓN ---
        EXISTING_ID_CEDULA = '1017000123'
        EXISTING_EMAIL = 'old@user.com'
        EXISTING_USERNAME = 'user_old'
        
        usuario_existente = Usuario.objects.create(
            username=EXISTING_USERNAME, 
            email=EXISTING_EMAIL, 
            rol=Usuario.Roles.ASISTENTE,
            first_name='Old', last_name='User', 
            telefono='1112223333'
        )
        usuario_existente.set_password('old_password_hashed') 
        usuario_existente.save()

        asistente_existente = Asistente.objects.create(usuario=usuario_existente)
        
        evento_2 = create_evento(self.admin, "Evento Reutilizacion", 'No tiene costo', 5, True)
        url_reutilizacion = reverse('crear_asistente', kwargs={'pk': evento_2.pk})
        
        # --- ACT (Asegurando que los datos enviados COINCIDEN con el usuario existente) ---
        data = {
            'id': EXISTING_ID_CEDULA, 
            'username': EXISTING_USERNAME, 
            'email': EXISTING_EMAIL,      
            'first_name': 'Old', 
            'last_name': 'User', 
            'telefono': '1112223333',
        } 
        
        response = self.client.post(url_reutilizacion, data=data, follow=True)
        
        # --- ASSERTIONS ---
        # ASSERT 1: No se crea un nuevo Usuario
        self.assertEqual(Usuario.objects.filter(email=EXISTING_EMAIL).count(), 1, "Se creó un usuario duplicado.")
        
        # ASSERT 2: Se crea un nuevo AsistenteEvento (Debe pasar con el formulario corregido)
        self.assertTrue(AsistenteEvento.objects.filter(
            asi_eve_evento_fk=evento_2, 
            asi_eve_asistente_fk=asistente_existente
        ).exists(), f"Fallo al crear AsistenteEvento. El formulario fue inválido. Respuesta: {response.status_code}")
        
        # ASSERT 3: Email enviado con placeholder de contraseña (CA-2.9)
        self.assertEqual(len(mail.outbox), 1, "Número incorrecto de emails enviados.")
        email = mail.outbox[0]
        self.assertIn("Tu contraseña actual", email.body)



    @patch('qrcode.make', return_value=MagicMock(save=MagicMock()))
    def test_cp_2_12_rechazo_asistente_duplicado(self, mock_qrcode):
        """Valida CA-2.4: Rechazo si ya existe un AsistenteEvento con el mismo email/evento."""
        
        # PRE: Inscribir un asistente inicialmente
        usuario = Usuario.objects.create(username='duplicate_user', email='duplicate@test.com', rol=Usuario.Roles.ASISTENTE)
        asistente = Asistente.objects.create(usuario=usuario)
        AsistenteEvento.objects.create(
            asi_eve_evento_fk=self.evento_gratuito,
            asi_eve_asistente_fk=asistente,
            asi_eve_estado='Aprobado',
            asi_eve_fecha_hora=date.today(),
            asi_eve_clave='oldclave'
        )
        
        # Sanity check
        self.assertEqual(AsistenteEvento.objects.filter(asi_eve_evento_fk=self.evento_gratuito, asi_eve_asistente_fk__usuario__email='duplicate@test.com').count(), 1)
        
        # ACT: Intentar inscribir al mismo usuario (mismo email) de nuevo
        data = self.base_data.copy()
        data.update({'username': 'duplicate_user_2', 'email': 'duplicate@test.com'})
        
        response = self.client.post(self.url_gratuito, data=data, follow=False)
        
        # ASSERT 1: Retorna al formulario (200 OK)
        self.assertEqual(response.status_code, 200)
        
        # ASSERT 2: Mensaje de error (CA-2.4)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn("Ya estás inscrito como asistente en este evento.", [m.message for m in messages])
        
        # ASSERT 3: No se crea registro duplicado
        self.assertEqual(AsistenteEvento.objects.filter(asi_eve_evento_fk=self.evento_gratuito, asi_eve_asistente_fk__usuario__email='duplicate@test.com').count(), 1)