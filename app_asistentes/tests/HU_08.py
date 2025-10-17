""" Como Asistente quiero Recibir notificaciones sobre los eventos en los que estoy inscrito para 
Estar al tanto de información relevante sobre el evento"""


from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.utils import timezone
from datetime import date, timedelta # Necesario si usas TransactionTestCase y creas fechas dinámicas

from app_usuarios.models import Usuario, AdministradorEvento, Asistente
from app_asistentes.models import AsistenteEvento
from app_admin_eventos.models import Evento
from django.conf import settings


# CLAVE: Si la prueba sigue fallando por IntegrityError (clave duplicada),
# cambia 'TestCase' por 'TransactionTestCase'.
class EnviarNotificacionAsistentesTest(TestCase):
    
    # Usaremos el setUp tradicional, asumiendo que TestCase funciona.
    def setUp(self):
        self.client = Client()

        # === Crear usuario administrador ===
        self.admin_user = Usuario.objects.create_user(
            username='admin',
            password='admin123',
            email='admin@example.com',
            rol='administrador_evento',
            cedula='1001'
        )
        # Usar get_or_create podría ser problemático si el ID colisiona.
        # Mejor usar create simple si la base de datos se limpia correctamente.
        self.admin_perfil = AdministradorEvento.objects.create(usuario=self.admin_user)

        # === Archivo simulado para el evento ===
        archivo_falso = SimpleUploadedFile(
            "programacion.pdf", b"Contenido de prueba", content_type="application/pdf"
        )
        
        # === Crear evento ===
        fecha_futura = date.today() + timedelta(days=30)
        self.evento = Evento.objects.create(
            eve_nombre="Evento de prueba",
            eve_descripcion="Un evento de prueba para tests",
            eve_estado="Publicado",
            eve_fecha_inicio=fecha_futura, # Usar fechas dinámicas para evitar problemas de eventos pasados
            eve_fecha_fin=fecha_futura + timedelta(days=2),
            eve_ciudad="Bogotá",
            eve_tienecosto="Sin costo",
            eve_capacidad=100,
            eve_administrador_fk=self.admin_perfil,
            eve_programacion=archivo_falso,
            eve_imagen=None
        )

        # === Crear usuarios asistentes ===
        self.usuario_aprobado = Usuario.objects.create_user(
            username='asistente_aprobado',
            password='test123',
            email='aprobado@example.com',
            rol='asistente',
            cedula='2001'
        )
        self.usuario_pendiente = Usuario.objects.create_user(
            username='asistente_pendiente',
            password='test123',
            email='pendiente@example.com',
            rol='asistente',
            cedula='2002'
        )

        # === Crear perfiles Asistente ===
        self.asistente_aprobado = Asistente.objects.create(usuario=self.usuario_aprobado)
        self.asistente_pendiente = Asistente.objects.create(usuario=self.usuario_pendiente)

        # === Archivos simulados para los campos obligatorios ===
        soporte_falso = SimpleUploadedFile("soporte.pdf", b"soporte", content_type="application/pdf")
        qr_falso = SimpleUploadedFile("qr.png", b"qrcontent", content_type="image/png")

        # === Crear inscripciones de asistentes ===
        self.inscripcion_aprobada = AsistenteEvento.objects.create(
            asi_eve_asistente_fk=self.asistente_aprobado,
            asi_eve_evento_fk=self.evento,
            asi_eve_fecha_hora=timezone.now(),
            asi_eve_estado='Aprobado', # Los estados deben coincidir con la vista: "Aprobado", "Pendiente"
            asi_eve_soporte=soporte_falso,
            asi_eve_qr=qr_falso,
            asi_eve_clave='clave123'
        )
        self.inscripcion_pendiente = AsistenteEvento.objects.create(
            asi_eve_asistente_fk=self.asistente_pendiente,
            asi_eve_evento_fk=self.evento,
            asi_eve_fecha_hora=timezone.now(),
            asi_eve_estado='Pendiente', # Los estados deben coincidir con la vista: "Aprobado", "Pendiente"
            asi_eve_soporte=soporte_falso,
            asi_eve_qr=qr_falso,
            asi_eve_clave='clave456'
        )

        # === Login del administrador ===
        self.client.login(username='admin', password='admin123')

        # === URL de la vista ===
        self.url = reverse('notificar_asi', args=[self.evento.id])

    # === CASO 1 ===
    def test_cp_as_not_001_envio_notificacion_a_aprobados(self):
        """Verifica que el administrador pueda enviar notificaciones a asistentes aprobados."""
        
        # La vista espera una lista de IDs de 'asistentes' y el 'mensaje'
        response = self.client.post(self.url, {
            'asistentes': [self.inscripcion_aprobada.pk], # ID de la inscripción
            'mensaje': 'Prueba de notificacion para aprobados'
        })
        
        # CLAVE: Esperamos 302 (Redirección Post/Redirect/Get)
        self.assertEqual(response.status_code, 302) 
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('aprobado@example.com', mail.outbox[0].to)
        # La vista usa 'Notificación sobre el evento: Nombre del evento'
        self.assertIn('Notificación sobre el evento', mail.outbox[0].subject)

    # === CASO 2 ===
    def test_cp_as_not_002_envio_notificacion_a_pendientes(self):
        """Verifica que el administrador pueda enviar notificaciones a asistentes pendientes."""
        
        response = self.client.post(self.url, {
            'asistentes': [self.inscripcion_pendiente.pk], # ID de la inscripción
            'mensaje': 'Prueba de notificacion para pendientes'
        })
        
        # CLAVE: Esperamos 302 (Redirección Post/Redirect/Get)
        self.assertEqual(response.status_code, 302) 
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('pendiente@example.com', mail.outbox[0].to)
        self.assertIn('Notificación sobre el evento', mail.outbox[0].subject)

    # === CASO 3 ===
    def test_cp_as_not_003_restriccion_por_rol(self):
        """Verifica que un usuario no administrador no pueda acceder a la vista."""
        
        self.client.logout()
        # Creamos y logueamos al usuario no administrador
        normal_user = Usuario.objects.create_user(
            username='no_admin',
            password='test123',
            email='noadmin@example.com',
            rol='asistente',
            cedula='2003'
        )
        self.client.login(username='no_admin', password='test123')
        
        # Intentamos acceder a la vista POST
        response = self.client.post(self.url, {
            'asistentes': [self.inscripcion_aprobada.pk], 
            'mensaje': 'Mensaje'
        })
        
        # CLAVE: El decorador admin_required probablemente redirige al login, lo que es 302.
        # Si la vista devuelve 403, mantén 403. Pero un 302 a '/login?next=...' es lo más común.
        # Ajustamos a 302 (redirección)
        self.assertEqual(response.status_code, 302) 
        self.assertIn(reverse('login_view'), response.url) 
        self.assertEqual(len(mail.outbox), 0) # No se debe enviar correo

    # === CASO EXTRA: Mensaje vacío (CP-3.2) ===
    def test_cp_as_not_004_mensaje_vacio_falla(self):
        """Verifica que falle si el mensaje está vacío."""
        response = self.client.post(self.url, {
            'asistentes': [self.inscripcion_aprobada.pk], 
            'mensaje': '' # Mensaje vacío
        })
        
        # La vista regresa un GET (200) y debe tener un mensaje de error
        self.assertEqual(response.status_code, 200) 
        self.assertContains(response, "El mensaje no puede estar vacío.")
        self.assertEqual(len(mail.outbox), 0)

    # === CASO EXTRA: Sin seleccionados (CP-3.3) ===
    def test_cp_as_not_005_sin_asistentes_seleccionados_falla(self):
        """Verifica que falle si no se selecciona ningún asistente."""
        response = self.client.post(self.url, {
            'asistentes': [], # Lista vacía
            'mensaje': 'Mensaje de prueba'
        })
        
        # La vista regresa un GET (200) y debe tener un mensaje de advertencia
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No seleccionaste ningún asistente.")
        self.assertEqual(len(mail.outbox), 0)




