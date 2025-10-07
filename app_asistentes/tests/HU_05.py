""" Como visitante web (asistente) Registrame a un evento para 
Poder asistir al mismo"""


from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.utils import timezone
from datetime import timedelta
import random
import string

# Importar Modelos y Formularios (asumidos)
from app_admin_eventos.models import Evento
from app_asistentes.models import AsistenteEvento
from app_usuarios.models import Usuario, AdministradorEvento, Asistente

# --- Setup General ---
class AsistenteRegistroTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # ... (La solución anterior para el IntegrityError con PK=9999) ...
        ADMIN_USER_ID = 9999
        # 1. Crear el Admin Usuario con un PK grande y fijo
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
        # 2. Crear el AdministradorEvento asociado
        cls.admin, _ = AdministradorEvento.objects.update_or_create(
            usuario=cls.user_admin
        )
        
        # --- Resto del Setup (Sin Cambios Relevantes) ---
        cls.fecha_proxima = timezone.now().date() + timedelta(days=7)

        # Evento 1: Sin Costo (Aprobación Automática)
        cls.evento_gratis = Evento.objects.create(
            eve_nombre="Conferencia Gratuita", 
            eve_descripcion="Gratuito",
            eve_estado="Publicado",
            eve_administrador_fk=cls.admin,
            eve_tienecosto='Sin costo',
            eve_capacidad=100, 
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima + timedelta(days=1), 
            eve_ciudad='Ciudad', eve_lugar='Lugar', eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf"), eve_imagen=SimpleUploadedFile("img.png", b"file")
        )

        # Evento 2: De Pago (Aprobación Pendiente)
        cls.evento_pago = Evento.objects.create(
            eve_nombre="Taller de Pago", 
            eve_descripcion="Con Costo",
            eve_estado="Publicado",
            eve_administrador_fk=cls.admin,
            eve_tienecosto='De pago',
            eve_capacidad=50,
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima + timedelta(days=1), 
            eve_ciudad='Ciudad', eve_lugar='Lugar', eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf"), eve_imagen=SimpleUploadedFile("img.png", b"file")
        )
        
        # Evento 3: Capacidad Agotada (Para CP-1.4)
        cls.evento_lleno = Evento.objects.create(
            eve_nombre="Capacidad Max", 
            eve_descripcion="Lleno",
            eve_estado="Publicado",
            eve_administrador_fk=cls.admin,
            eve_tienecosto='Sin costo',
            eve_capacidad=0, # Capacidad 0 para la prueba
            eve_fecha_inicio=cls.fecha_proxima, eve_fecha_fin=cls.fecha_proxima + timedelta(days=1), 
            eve_ciudad='Ciudad', eve_lugar='Lugar', eve_programacion=SimpleUploadedFile("prog.pdf", b"pdf"), eve_imagen=SimpleUploadedFile("img.png", b"file")
        )
        
        # URL de registro
        cls.url_gratis = reverse('crear_asistente', kwargs={'pk': cls.evento_gratis.pk})
        cls.url_pago = reverse('crear_asistente', kwargs={'pk': cls.evento_pago.pk})
        cls.url_lleno = reverse('crear_asistente', kwargs={'pk': cls.evento_lleno.pk})
        

        # === AÑADIR: Definición de datos del formulario (la variable faltante) ===
        cls.participante_data = {
            'id': '123456789',
            'username': 'nuevoasistente',
            'email': 'nuevo@example.com',
            'telefono': '3001234567',
            'first_name': 'Juan',
            'last_name': 'Perez',
            # Asumiendo que el formulario de registro de asistente NO pide password
            # Si pide password, debes añadirlo aquí: 'password': 'pass', 'password2': 'pass'
        }



    def setUp(self):
        self.client = Client()
        mail.outbox = [] # Limpiar bandeja de salida de correos

        # Datos base de un nuevo asistente
        self.new_user_data = {
            'id': 123456,
            'username': 'nuevoasistente',
            'email': 'nuevo@example.com',
            'telefono': '3001234567',
            'first_name': 'Juan',
            'last_name': 'Perez',
        }
        # Archivo de prueba para soporte
        self.dummy_file = SimpleUploadedFile("soporte.pdf", b"soporte_pago_content", content_type="application/pdf")
    
    
    # ----------------------------------------------------------------------
    # CP-1.1: Registro Exitoso en Evento 'Sin Costo' (Nuevo Usuario) (CA-1.1, CA-1.5)
    # ----------------------------------------------------------------------
    def test_cp_1_1_registro_gratis_exitoso_nuevo_usuario(self):
        """Valida registro exitoso, estado 'Aprobado', capacidad -1, generación de QR/Clave y envío de email."""
        
        initial_capacidad = self.evento_gratis.eve_capacidad

        response = self.client.post(self.url_gratis, self.new_user_data, follow=True)

        # 1. Validación de Redirección y Mensaje de Éxito
        self.assertRedirects(response, reverse('pagina_principal'))
        self.assertContains(response, 'La preinscripción fue exitosa')
        
        # 2. Validación de Creación de Objetos
        self.assertTrue(Usuario.objects.filter(email='nuevo@example.com').exists())
        user = Usuario.objects.get(email='nuevo@example.com')
        self.assertTrue(Asistente.objects.filter(usuario=user).exists())
        self.assertTrue(AsistenteEvento.objects.filter(asi_eve_asistente_fk__usuario=user, asi_eve_evento_fk=self.evento_gratis).exists())
        asistente_evento = AsistenteEvento.objects.get(asi_eve_asistente_fk__usuario=user)

        # 3. Validación de Estado y Capacidad (CA-1.1, CA-1.5)
        self.assertEqual(asistente_evento.asi_eve_estado, "Aprobado", 
                         "CA-1.1 FALLO: Evento gratuito no se marcó como 'Aprobado'.")
        self.evento_gratis.refresh_from_db()
        self.assertEqual(self.evento_gratis.eve_capacidad, initial_capacidad - 1, 
                         "CA-1.5 FALLO: La capacidad del evento no disminuyó.")

        # 4. Validación de QR y Clave (CA-1.5)
        self.assertTrue(asistente_evento.asi_eve_clave, "CA-1.5 FALLO: Clave de acceso no generada.")
        self.assertTrue(asistente_evento.asi_eve_qr, "CA-1.5 FALLO: Archivo QR no adjunto al registro.")

        # 5. Validación de Correo Electrónico (CA-1.5)
        self.assertEqual(len(mail.outbox), 1, "CA-1.5 FALLO: No se envió el correo de confirmación.")
        email_msg = mail.outbox[0]
        self.assertIn(asistente_evento.asi_eve_clave, email_msg.body, "CA-1.5 FALLO: Clave no incluida en el cuerpo del email.")
        self.assertEqual(len(email_msg.attachments), 1, "CA-1.5 FALLO: QR no adjunto al email.")


    # ----------------------------------------------------------------------
    # CP-1.2: Registro Exitoso en Evento 'De Pago' con Soporte (CA-1.2)
    # ----------------------------------------------------------------------
    def test_cp_1_2_registro_pago_exitoso_con_soporte(self):
        """Valida registro exitoso, estado 'Pendiente' y que el soporte de pago fue cargado."""
        
        initial_capacidad = self.evento_pago.eve_capacidad
        
        post_data = self.new_user_data.copy()
        post_data['email'] = 'pago@example.com' # Email diferente para unicidad

        response = self.client.post(self.url_pago, 
                                    {**post_data, 'asi_eve_soporte': self.dummy_file}, 
                                    follow=True)

        # 1. Validación de Redirección y Mensaje de Éxito
        self.assertRedirects(response, reverse('pagina_principal'))
        self.assertContains(response, 'La preinscripción fue exitosa')
        
        # 2. Validación de Estado, Soporte y Capacidad (CA-1.2)
        user = Usuario.objects.get(email='pago@example.com')
        asistente_evento = AsistenteEvento.objects.get(asi_eve_asistente_fk__usuario=user, asi_eve_evento_fk=self.evento_pago)

        self.assertEqual(asistente_evento.asi_eve_estado, "Pendiente", 
                         "CA-1.2 FALLO: Evento de pago no se marcó como 'Pendiente'.")
        self.assertTrue(asistente_evento.asi_eve_soporte, "CA-1.2 FALLO: Soporte de pago no fue cargado.")
        self.evento_pago.refresh_from_db()
        self.assertEqual(self.evento_pago.eve_capacidad, initial_capacidad - 1, 
                         "CA-1.2 FALLO: La capacidad del evento no disminuyó.")
        
        # 3. Validación de Correo (Sin QR adjunto)
        self.assertEqual(len(mail.outbox), 1, "FALLO: No se envió el correo de confirmación.")
        self.assertEqual(len(mail.outbox[0].attachments), 0, "FALLO: QR adjunto a evento de pago.")


    # ----------------------------------------------------------------------
    # CP-1.3: Registro Fallido en Evento 'De Pago' por Falta de Soporte (CA-1.2)
    # ----------------------------------------------------------------------
    def test_cp_1_3_registro_pago_fallido_sin_soporte(self):
        """Valida que un evento 'De Pago' requiere soporte obligatoriamente."""
        
        initial_count = AsistenteEvento.objects.count()

        response = self.client.post(self.url_pago, self.new_user_data, follow=False)

        # 1. Validación de Respuesta (Renderiza formulario con error)
        self.assertEqual(response.status_code, 200, "FALLO: Debería renderizar el formulario con errores, no redireccionar.")
        self.assertContains(response, "Debe cargar el comprobante de pago para este evento.")
        
        # 2. Validación de No Creación de Objetos
        self.assertEqual(AsistenteEvento.objects.count(), initial_count, "CA-1.2 FALLO: Se creó un AsistenteEvento sin soporte de pago.")


    # ----------------------------------------------------------------------
    # CP-1.4: Registro Fallido por Capacidad Agotada (CA-1.4)
    # ----------------------------------------------------------------------
    def test_cp_1_4_registro_fallido_capacidad_agotada(self):
        """Valida que el registro falla si eve_capacidad es 0."""
        
        # 1. Obtiene los datos del formulario (Ahora existe self.participante_data)
        data = self.participante_data.copy()
        
        # 2. Intenta POST en el evento sin capacidad (cls.evento_lleno)
        response = self.client.post(self.url_lleno, data, follow=True)
        
        # CRITERIO DE ACEPTACIÓN CP-1.4: El sistema debe mostrar un mensaje de error si la capacidad es cero.
        expected_message = "No hay más cupos disponibles para este evento."
        
        # 3. Validar el mensaje de error (usando msg_prefix)
        self.assertContains(
            response, 
            expected_message, 
            status_code=200, # La vista regresa la misma página con el mensaje
            msg_prefix="CA-1.4 FALLO: No se mostró el mensaje de cupos agotados."
        )
        
        # 4. Validar que NO se creó el registro AsistenteEvento
        self.assertFalse(
            AsistenteEvento.objects.filter(asi_eve_evento_fk=self.evento_lleno).exists(),
            "CA-1.4 FALLO: Se creó un registro AsistenteEvento a pesar de la capacidad agotada."
        )

        # 5. Validar que la respuesta es 200 (se mantiene en la misma página)
        self.assertEqual(
            response.status_code, 
            200, 
            "CA-1.4 FALLO: La vista no regresó la página de registro (Status 200)."
        )


    # ----------------------------------------------------------------------
    # CP-1.5: Registro Fallido por Duplicidad de Inscripción (CA-1.4)
    # ----------------------------------------------------------------------
    def test_cp_1_5_registro_fallido_duplicidad(self):
        """Valida que no se permite inscribirse dos veces como asistente al mismo evento."""
        
        # El setup debe haber creado ya un usuario (cls.usuario_asistente) y un AsistenteEvento
        # para este test, pero dado que no vemos el setup completo, simularemos un usuario 
        # y una pre-inscripción para garantizar la duplicidad.
        
        # Datos del asistente duplicado (usamos un correo diferente para no chocar con otros tests)
        duplicate_data = self.participante_data.copy()
        duplicate_data['email'] = 'asistente_duplicado@test.com'
        duplicate_data['id'] = '987654321'
        
        # 1. Primera inscripción (La que debe ser exitosa)
        response_initial = self.client.post(self.url_gratis, duplicate_data, follow=True)
        self.assertEqual(response_initial.status_code, 200, "Setup falló: La primera inscripción debe ser exitosa.")
        self.assertTrue(Usuario.objects.filter(email='asistente_duplicado@test.com').exists(), "Setup falló: El usuario de la primera inscripción no se creó.")

        # 2. Intento de segunda inscripción con los mismos datos
        response_duplicate = self.client.post(self.url_gratis, duplicate_data, follow=True)
        
        # Mensaje de error esperado (tomado de la traza)
        expected_message = "Ya estás inscrito como asistente en este evento."
        
        # CRITERIO DE ACEPTACIÓN CP-1.5: Se debe denegar la inscripción y mostrar un mensaje de error.
        
        # CORRECCIÓN DE LA SINTAXIS: Usar msg_prefix nombrado
        self.assertContains(
            response_duplicate, 
            expected_message, 
            status_code=200, # Se espera que regrese a la misma página con el error.
            msg_prefix="CA-1.5 FALLO: No se mostró el mensaje de duplicidad." # Corrección de CA-1.4 a CA-1.5
        )
        
        # Validación de No Creación de Objetos (Debe haber solo UN registro AsistenteEvento)
        self.assertEqual(
            AsistenteEvento.objects.filter(
                asi_eve_evento_fk=self.evento_gratis, 
                asi_eve_asistente_fk__usuario__email='asistente_duplicado@test.com'
            ).count(),
            1,
            "CA-1.5 FALLO: Se creó más de un registro de AsistenteEvento para el mismo usuario y evento."
        )

        # Opcional: Validar que el usuario solo tiene el rol de Asistente
        user = Usuario.objects.get(email='asistente_duplicado@test.com')
        self.assertEqual(user.rol, Usuario.Roles.ASISTENTE, "CA-1.5 FALLO: El rol del usuario no es el esperado.")


    # ----------------------------------------------------------------------
    # CP-1.6: Registro Exitoso Reutilizando Usuario Existente (CA-1.3, CA-1.6)
    # ----------------------------------------------------------------------
    def test_cp_1_6_registro_reutiliza_usuario_existente(self):
        """Valida la reutilización de un Usuario existente por email y creación de un nuevo AsistenteEvento."""
        
        # Precondición: Crear un Usuario existente que no es asistente en este evento
        existing_user = Usuario.objects.create_user(
            username='existente', email='existente@test.com', password='password123', rol=Usuario.Roles.VISITANTE
        )
        # Nota: El Asistente asociado puede o no existir, el view usa get_or_create.

        post_data = {
            'id': 999999, # Este ID debería ser ignorado si el email coincide
            'username': 'otro_username', # Este username debería ser ignorado si el email coincide
            'email': 'existente@test.com',
            'telefono': '3009999999',
            'first_name': 'NombreExistente',
            'last_name': 'ApellidoExistente',
        }
        
        initial_user_count = Usuario.objects.count()

        response = self.client.post(self.url_gratis, post_data, follow=True)

        # 1. Validación de Redirección y Mensaje de Éxito
        self.assertRedirects(response, reverse('pagina_principal'))
        self.assertContains(response, 'La preinscripción fue exitosa')
        
        # 2. Validación de Reutilización de Usuario (CA-1.3)
        self.assertEqual(Usuario.objects.count(), initial_user_count, 
                         "CA-1.3 FALLO: Se creó un nuevo Usuario en lugar de reutilizar el existente.")
        reused_user = Usuario.objects.get(email='existente@test.com')
        self.assertEqual(reused_user.pk, existing_user.pk, 
                         "CA-1.3 FALLO: El usuario reutilizado no coincide con el original.")
        
        # 3. Validación de AsistenteEvento
        self.assertTrue(AsistenteEvento.objects.filter(asi_eve_asistente_fk__usuario=reused_user, asi_eve_evento_fk=self.evento_gratis).exists())
        
        # 4. Validación de datos ignorados (CA-1.6)
        # El username y ID del formulario no deben haber sobrescrito los del usuario existente.
        self.assertNotEqual(reused_user.username, post_data['username'], 
                            "CA-1.6 FALLO: El username existente fue sobrescrito.")
        # El ID es un campo ficticio del formulario, pero verificamos que los datos del usuario no cambien.
        self.assertNotEqual(reused_user.first_name, post_data['first_name'],
                            "CA-1.6 FALLO: Los datos del usuario existente fueron sobrescritos.")