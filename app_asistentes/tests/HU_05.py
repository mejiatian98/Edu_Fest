""" Como visitante web (asistente) Registrame a un evento para 
Poder asistir al mismo"""

from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

# Importar Modelos (Asegúrate de que las importaciones son correctas)
from app_admin_eventos.models import Evento 
from app_asistentes.models import AsistenteEvento
from app_usuarios.models import Usuario, AdministradorEvento, Asistente, Participante, Evaluador 
from app_participantes.models import ParticipanteEvento
from app_evaluadores.models import EvaluadorEvento
from django.db.models.fields.files import FieldFile 


# --- Setup General y Casos de Prueba ---
class AsistenteRegistroTest(TestCase):
    
    @classmethod
    def setUpTestData(cls): # Usar setUpTestData para objetos que no cambian
        
        # 1. Setup de Administrador para Eventos
        ADMIN_USER_ID = 9999
        
        cls.user_admin, _ = Usuario.objects.update_or_create(
            pk=ADMIN_USER_ID,
            defaults={
                'username': 'admin_test_9999', 
                'email': 'admin_9999@test.com', 
                'password': make_password('password123'), 
                'rol': Usuario.Roles.ADMIN_EVENTO, 
                'is_staff': True
            }
        )

        cls.admin, _ = AdministradorEvento.objects.update_or_create(
            usuario=cls.user_admin,
            defaults={'cedula': '11111'}
        )
        
        cls.fecha_proxima = timezone.now().date() + timedelta(days=7)

        # 2. Evento 1: Sin Costo (Aprobación Automática)
        cls.evento_gratis = Evento.objects.create(
            eve_nombre="Conferencia Gratuita", eve_descripcion="Gratuito", eve_estado="Publicado",
            eve_administrador_fk=cls.admin, eve_tienecosto='Sin costo', eve_capacidad=100, 
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima + timedelta(days=1), 
            eve_ciudad='Ciudad', eve_lugar='Lugar', 
            eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf"), 
            eve_imagen=SimpleUploadedFile("img.png", b"file")
        )

        # 3. Evento 2: De Pago (Aprobación Pendiente)
        cls.evento_pago = Evento.objects.create(
            eve_nombre="Taller de Pago", eve_descripcion="Con Costo", eve_estado="Publicado",
            eve_administrador_fk=cls.admin, eve_tienecosto='De pago', eve_capacidad=50,
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima + timedelta(days=1), 
            eve_ciudad='Ciudad', eve_lugar='Lugar', 
            eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf"), 
            eve_imagen=SimpleUploadedFile("img.png", b"file")
        )
        
        # 4. Evento 3: Capacidad Agotada
        cls.evento_lleno = Evento.objects.create(
            eve_nombre="Capacidad Max", eve_descripcion="Lleno", eve_estado="Publicado",
            eve_administrador_fk=cls.admin, eve_tienecosto='Sin costo', eve_capacidad=0, 
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima + timedelta(days=1), 
            eve_ciudad='Ciudad', eve_lugar='Lugar', 
            eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf"), 
            eve_imagen=SimpleUploadedFile("img.png", b"file")
        )
        
        # 5. URLs
        cls.url_gratis = reverse('crear_asistente', kwargs={'pk': cls.evento_gratis.pk})
        cls.url_pago = reverse('crear_asistente', kwargs={'pk': cls.evento_pago.pk})
        cls.url_lleno = reverse('crear_asistente', kwargs={'pk': cls.evento_lleno.pk})
        

    def setUp(self):
        self.client = Client()
        mail.outbox = [] # Limpiar bandeja de salida de correos

        # Datos base de un nuevo asistente 
        self.new_user_data = {
            'cedula': 123456789,
            'username': 'nuevoasistente',
            'email': 'nuevo@example.com',
            'telefono': '3001234567',
            'first_name': 'Juan',
            'last_name': 'Perez',
        }
        # Archivo de prueba para soporte
        self.dummy_file = SimpleUploadedFile("soporte.pdf", b"soporte_pago_content", content_type="application/pdf")
        
        # FIX: Patching para simular el guardado de archivos (QR)
        self.qr_patch = patch('django.db.models.fields.files.FieldFile.save')
        self.mock_qr = self.qr_patch.start()
        self.mock_qr.return_value = None 


    def tearDown(self):
        # Asegúrate de detener el patch después de cada prueba
        self.qr_patch.stop()

    # ----------------------------------------------------------------------
    # CP-1.1: Registro Exitoso en Evento 'Sin Costo' (Nuevo Usuario) (CA-1.1, CA-1.5)
    # ----------------------------------------------------------------------
    # FIX: Se elimina el patch estático de la clave, solo se verifica su existencia
    def test_cp_1_1_registro_gratis_exitoso_nuevo_usuario(self):
        """Valida registro exitoso, estado 'Aprobado', capacidad -1, generación de QR/Clave y envío de email."""
        
        post_data = self.new_user_data.copy()
        post_data.update({'email': 'gratis1@test.com', 'cedula': 1000})

        initial_capacidad = self.evento_gratis.eve_capacidad
        
        response = self.client.post(self.url_gratis, post_data, follow=True)

        # 1. Validación de Redirección y Mensaje de Éxito
        self.assertRedirects(response, reverse('pagina_principal'))
        self.assertContains(response, 'La preinscripción fue exitosa')
        
        # 2. Validación de Creación de Objetos
        user = Usuario.objects.get(email='gratis1@test.com')
        asistente_evento = AsistenteEvento.objects.get(asi_eve_asistente_fk__usuario=user, asi_eve_evento_fk=self.evento_gratis)

        # 3. Validación de Estado y Capacidad (CA-1.1, CA-1.5)
        self.assertEqual(asistente_evento.asi_eve_estado, "Aprobado", "CA-1.1 FALLO: Estado incorrecto.")
        self.evento_gratis.refresh_from_db()
        self.assertEqual(self.evento_gratis.eve_capacidad, initial_capacidad - 1, "CA-1.5 FALLO: Capacidad no disminuyó.")

        # 4. Validación de QR y Clave (CA-1.5)
        # FIX: Se verifica que la clave no sea nula/vacía, usando el valor REAL generado
        self.assertTrue(asistente_evento.asi_eve_clave, "CA-1.5 FALLO: Clave de acceso no generada (es nula o vacía).")
        self.mock_qr.assert_called() 
        self.assertTrue(asistente_evento.asi_eve_qr, "CA-1.5 FALLO: Archivo QR no adjunto (simulado).")

        # 5. Validación de Correo Electrónico (CA-1.5)
        self.assertEqual(len(mail.outbox), 1, "CA-1.5 FALLO: No se envió el correo de confirmación.")
        email_msg = mail.outbox[0]
        # FIX: Se usa la clave real para la aserción
        self.assertTrue(asistente_evento.asi_eve_clave in email_msg.body, "CA-1.5 FALLO: Clave no presente en el email.")
        self.assertTrue(email_msg.attachments, "CA-1.5 FALLO: QR no adjunto al email.")


    # ----------------------------------------------------------------------
    # CP-1.2: Registro Exitoso en Evento 'De Pago' con Soporte (CA-1.2)
    # ----------------------------------------------------------------------
    def test_cp_1_2_registro_pago_exitoso_con_soporte(self):
        """Valida registro exitoso, estado 'Pendiente' y que el soporte de pago fue cargado."""
        
        initial_capacidad = self.evento_pago.eve_capacidad
        
        post_data = self.new_user_data.copy()
        post_data.update({
            'email': 'pago@example.com', 
            'cedula': 2000,
            'asi_eve_soporte': self.dummy_file
        })

        response = self.client.post(self.url_pago, post_data, follow=True)

        # 1. Validación de Redirección y Mensaje de Éxito
        self.assertRedirects(response, reverse('pagina_principal'))
        self.assertContains(response, 'La preinscripción fue exitosa')
        
        # 2. Validación de Estado, Soporte y Capacidad (CA-1.2)
        user = Usuario.objects.get(email='pago@example.com')
        asistente_evento = AsistenteEvento.objects.get(asi_eve_asistente_fk__usuario=user, asi_eve_evento_fk=self.evento_pago)

        self.assertEqual(asistente_evento.asi_eve_estado, "Pendiente", "CA-1.2 FALLO: Estado incorrecto.")
        self.assertTrue(asistente_evento.asi_eve_soporte.name.endswith('soporte.pdf'), "CA-1.2 FALLO: Soporte de pago no fue cargado.")
        self.evento_pago.refresh_from_db()
        self.assertEqual(self.evento_pago.eve_capacidad, initial_capacidad - 1, "CA-1.2 FALLO: Capacidad no disminuyó.")
        
        # 3. Validación de Correo (Sin QR adjunto)
        self.assertEqual(len(mail.outbox), 1, "FALLO: No se envió el correo de confirmación.")
        self.assertEqual(len(mail.outbox[0].attachments), 0, "FALLO: QR adjunto a evento de pago Pendiente.")


    # ----------------------------------------------------------------------
    # CP-1.3: Registro Fallido en Evento 'De Pago' por Falta de Soporte (CA-1.2)
    # ----------------------------------------------------------------------
    def test_cp_1_3_registro_pago_fallido_sin_soporte(self):
        """Valida que un evento 'De Pago' requiere soporte obligatoriamente."""
        
        initial_count = AsistenteEvento.objects.count()
        post_data = self.new_user_data.copy()
        post_data.update({'email': 'sin_soporte@test.com', 'cedula': 3000})

        response = self.client.post(self.url_pago, post_data, follow=False)

        # 1. Validación de Respuesta (Renderiza formulario con error)
        self.assertEqual(response.status_code, 200, "CA-1.2 FALLO: Debería renderizar el formulario con errores (Status 200).")
        self.assertContains(response, "Debe cargar el comprobante de pago para este evento.") 
        
        # 2. Validación de No Creación de Objetos
        self.assertEqual(AsistenteEvento.objects.count(), initial_count, "CA-1.2 FALLO: Se creó un AsistenteEvento sin soporte de pago.")


    # ----------------------------------------------------------------------
    # CP-1.4: Registro Fallido por Capacidad Agotada (CA-1.4)
    # ----------------------------------------------------------------------
    def test_cp_1_4_registro_fallido_capacidad_agotada(self):
        """Valida que el registro falla si eve_capacidad es 0."""
        
        data = self.new_user_data.copy()
        data.update({'email': 'cupo_agotado@test.com', 'cedula': 4000})

        response = self.client.post(self.url_lleno, data, follow=True)
        
        expected_message = "No hay más cupos disponibles para este evento."
        
        # 1. Validar el mensaje de error y status (CA-1.4)
        self.assertContains(
            response, 
            expected_message, 
            status_code=200, 
            msg_prefix="CA-1.4 FALLO: No se mostró el mensaje de cupos agotados."
        )
        
        # 2. Validar que NO se creó el registro AsistenteEvento
        self.assertFalse(
            AsistenteEvento.objects.filter(asi_eve_evento_fk=self.evento_lleno).exists(),
            "CA-1.4 FALLO: Se creó un registro AsistenteEvento a pesar de la capacidad agotada."
        )


    # ----------------------------------------------------------------------
    # CP-1.5: Registro Fallido por Duplicidad de Inscripción (CA-1.6)
    # ----------------------------------------------------------------------
    # Se mantiene el patch para clave solo si la clave es necesaria para el setup de la primera inscripción
    def test_cp_1_5_registro_fallido_duplicidad(self):
        """Valida que no se permite inscribirse dos veces como asistente al mismo evento."""
        
        duplicate_email = 'asistente_duplicado@test.com'
        duplicate_data = self.new_user_data.copy()
        duplicate_data.update({'email': duplicate_email, 'cedula': 5000})
        
        # 1. Primera inscripción (SETUP - Debe ser exitosa)
        self.client.post(self.url_gratis, duplicate_data, follow=True)
        user = Usuario.objects.get(email=duplicate_email)
        initial_count = AsistenteEvento.objects.filter(asi_eve_asistente_fk__usuario=user, asi_eve_evento_fk=self.evento_gratis).count()
        self.assertEqual(initial_count, 1, "Setup falló: La primera inscripción no creó el AsistenteEvento.")

        # 2. Intento de segunda inscripción (TEST)
        response_duplicate = self.client.post(self.url_gratis, duplicate_data, follow=False) 
        
        # FIX: Ajustar el mensaje esperado al texto real de la plantilla
        expected_message = "Ya estás inscrito como asistente en este evento." 
        
        # 3. Validación de Denegación y Mensaje de Error (CA-1.6)
        self.assertContains(
            response_duplicate, 
            expected_message, 
            status_code=200, 
            msg_prefix="CA-1.6 FALLO: No se mostró el mensaje de duplicidad."
        )
        
        # 4. Validación de No Creación de Objetos (Debe haber solo UN registro)
        final_count = AsistenteEvento.objects.filter(
            asi_eve_evento_fk=self.evento_gratis, 
            asi_eve_asistente_fk__usuario__email=duplicate_email
        ).count()
        self.assertEqual(final_count, 1, "CA-1.6 FALLO: Se creó más de un registro de AsistenteEvento.")


    # ----------------------------------------------------------------------
    # CP-1.6: Registro Exitoso Reutilizando Usuario Existente (CA-1.3, CA-1.6)
    # ----------------------------------------------------------------------
    # Se mantiene el patch para clave solo si la clave es necesaria para el test
    @patch('app_asistentes.models.AsistenteEvento.asi_eve_clave', 'TESTCLAVE_6')
    def test_cp_1_6_registro_reutiliza_usuario_existente(self):
        """Valida la reutilización de un Usuario existente por email, creando el perfil Asistente y el registro EventoAsistente."""
        
        # Precondición: Crear un Usuario existente (rol VISITANTE)
        existing_email = 'existente@test.com'
        existing_user = Usuario.objects.create_user(
            username='existente_user', email=existing_email, password='password123', rol=Usuario.Roles.VISITANTE
        )
        initial_user_count = Usuario.objects.count()
        
        # Datos del formulario con el email existente y nueva cédula (para el perfil Asistente)
        post_data = {
            'cedula': 6000, 
            'username': 'nuevo_username', 
            'email': existing_email, 
            'telefono': '3009999999',
            'first_name': 'NuevoNombre',
            'last_name': 'NuevoApellido',
        }
        
        response = self.client.post(self.url_gratis, post_data, follow=True)

        # 1. Validación de Redirección y Mensaje de Éxito
        self.assertRedirects(response, reverse('pagina_principal'))
        self.assertContains(response, 'La preinscripción fue exitosa')
        
        # 2. Validación de Reutilización de Usuario (CA-1.3)
        self.assertEqual(Usuario.objects.count(), initial_user_count, "CA-1.3 FALLO: Se creó un nuevo Usuario.")
        reused_user = Usuario.objects.get(email=existing_email)
        self.assertEqual(reused_user.pk, existing_user.pk, "CA-1.3 FALLO: El usuario reutilizado no coincide.")
        
        # 3. Validación de Creación del Perfil Asistente y AsistenteEvento
        asistente_profile = Asistente.objects.get(usuario=reused_user)
        self.assertEqual(asistente_profile.cedula, '6000', "CA-1.3 FALLO: Cédula del perfil Asistente incorrecta.")
        self.assertTrue(AsistenteEvento.objects.filter(asi_eve_asistente_fk__usuario=reused_user, asi_eve_evento_fk=self.evento_gratis).exists(), "FALLO: No se creó el registro AsistenteEvento.")
        
        # 4. Validación de datos de Usuario (CA-1.6)
        self.assertEqual(reused_user.username, 'existente_user', "CA-1.6 FALLO: El username existente fue sobrescrito.")
        
        # FIX: La aserción que falló. La lógica de producción debe actualizar el rol a ASISTENTE.
        # Si la lógica no existe, debes añadirla en la vista/modelo.
        self.assertEqual(reused_user.rol, Usuario.Roles.ASISTENTE, "CA-1.6 FALLO: El rol no fue actualizado a ASISTENTE.")
        

    # ----------------------------------------------------------------------
    # CP-1.7: Registro Fallido por Conflicto de Rol (Participante) (CA-1.6)
    # ----------------------------------------------------------------------
    def test_cp_1_7_registro_fallido_conflicto_rol_participante(self):
        """Valida que un usuario ya inscrito como Participante no puede inscribirse como Asistente."""

        # 1. Setup: Crear Usuario y ParticipanteEvento
        conflicto_email = 'conflicto_par@test.com'
        conflicto_user = Usuario.objects.create_user(
            username='user_conflicto', email=conflicto_email, password='pass', rol=Usuario.Roles.PARTICIPANTE, first_name='Conflict', last_name='User'
        )
        participante_profile = Participante.objects.create(usuario=conflicto_user, cedula='7000')
        ParticipanteEvento.objects.create(
            par_eve_participante_fk=participante_profile, 
            par_eve_evento_fk=self.evento_gratis, 
            par_eve_estado='Aprobado', 
            par_eve_clave='PARTCLAVE'
        )
        
        # 2. Intento de inscripción como Asistente (mismo email/cédula)
        post_data = self.new_user_data.copy()
        post_data.update({'cedula': '7000', 'email': conflicto_email})
        
        # FIX: Seguir la redirección (follow=True) para encontrar el mensaje de error de Django.
        response = self.client.post(self.url_gratis, post_data, follow=True)
        
        # Mensaje de error esperado
        expected_message = "Este usuario ya está inscrito como Participante en este evento." 
        
        # 3. Validación de Denegación (CA-1.6)
        self.assertContains(
            response, 
            expected_message, 
            status_code=200, # La respuesta final después de la redirección
            msg_prefix="CA-1.6 FALLO: No se detectó el conflicto de rol Participante/Asistente."
        )
        self.assertFalse(AsistenteEvento.objects.filter(asi_eve_asistente_fk__usuario=conflicto_user).exists(), "CA-1.6 FALLO: Se creó el registro AsistenteEvento a pesar del conflicto de rol.")