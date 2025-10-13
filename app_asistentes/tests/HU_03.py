""" Como visitante web quiero Acceder a 
información detallada sobre los eventos de mi interés para 
Tener mayor claridad sobre mi posibilidad e interés de asistir"""

from django.test import TestCase, Client
from django.urls import reverse
from app_admin_eventos.models import Evento
from app_usuarios.models import Usuario, Asistente, AdministradorEvento as UserAdminEvento 
from datetime import date

class EventoDetailViewVisitanteTest(TestCase):
    """Pruebas para la vista de detalle de evento para Visitantes Web."""

    @classmethod
    def setUpTestData(cls):
        """
        Configura los datos inmutables de la base de datos una sola vez 
        para toda la clase de pruebas, resolviendo el error de Duplicate Entry.
        """
        # 1. Crear Administrador de Evento
        cls.admin_user = Usuario.objects.create_user(
            username='admin_test_hu3_01', 
            email='admin_hu3_01@test.com', 
            password='password123', 
            rol=Usuario.Roles.ADMIN_EVENTO,
            cedula='12345678_HU3_01'
        )
        cls.admin_perfil = UserAdminEvento.objects.create(usuario=cls.admin_user)
        
        # 2. Crear Eventos
        cls.evento_publicado = Evento.objects.create(
            eve_nombre='Evento Público HU3',
            eve_descripcion='Descripción pública',
            eve_ciudad='Ciudad Publicada',
            eve_lugar='Lugar Publicado',
            eve_fecha_inicio=date(2025, 12, 1),
            eve_fecha_fin=date(2025, 12, 5),
            eve_estado='Publicado',
            eve_imagen='test_pub.jpg',
            eve_administrador_fk=cls.admin_perfil,
            eve_tienecosto='No',
            eve_capacidad=100,
            eve_programacion='programacion_pub.pdf'
        )

        cls.evento_finalizado = Evento.objects.create(
            eve_nombre='Evento Finalizado HU3',
            eve_descripcion='Descripción finalizada',
            eve_ciudad='Ciudad Finalizada',
            eve_lugar='Lugar Finalizado',
            eve_fecha_inicio=date(2025, 1, 1),
            eve_fecha_fin=date(2025, 1, 5),
            eve_estado='Finalizado',
            eve_imagen='test_fin.jpg',
            eve_administrador_fk=cls.admin_perfil,
            eve_tienecosto='Si',
            eve_capacidad=50,
            eve_programacion='programacion_fin.pdf'
        )

        cls.evento_cancelado = Evento.objects.create(
            eve_nombre='Evento Cancelado HU3',
            eve_descripcion='Descripción cancelada',
            eve_ciudad='Ciudad Cancelada',
            eve_lugar='Lugar Cancelado',
            eve_fecha_inicio=date(2025, 11, 1),
            eve_fecha_fin=date(2025, 11, 5),
            eve_estado='Cancelado',
            eve_imagen='test_can.jpg',
            eve_administrador_fk=cls.admin_perfil,
            eve_tienecosto='No',
            eve_capacidad=100,
            eve_programacion='programacion_can.pdf'
        )
        
        # 3. Crear usuario Asistente
        cls.asistente_user = Usuario.objects.create_user(
            username='asi_test_hu3_01', 
            email='asi_hu3_01@test.com', 
            password='password123', 
            rol=Usuario.Roles.ASISTENTE,
            cedula='87654321_HU3_01'
        )
        cls.asistente_perfil = Asistente.objects.create(usuario=cls.asistente_user)

    def setUp(self):
        """Inicializa el cliente de pruebas antes de cada método."""
        self.client = Client()

    # --- Casos de Prueba Funcionales (Visitante) ---

    def test_cp01_acceso_evento_publicado_visitante(self):
        """Prueba CA01/CA04: Acceso a un evento Publicado (200 OK y contenido)."""
        url = reverse('ver_info_evento_vis', kwargs={'pk': self.evento_publicado.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200, "Debe permitir acceso a evento Publicado.")
        self.assertContains(response, self.evento_publicado.eve_nombre)

    def test_cp02_acceso_evento_finalizado_visitante(self):
        """Prueba CA02/CA04: Acceso a un evento Finalizado (200 OK y contenido)."""
        url = reverse('ver_info_evento_vis', kwargs={'pk': self.evento_finalizado.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200, "Debe permitir acceso a evento Finalizado.")
        self.assertContains(response, self.evento_finalizado.eve_nombre)

    def test_cp03_no_acceso_evento_cancelado_visitante(self):
        """Prueba CA03: NO acceso a un evento Cancelado (404 Not Found)."""
        url = reverse('ver_info_evento_vis', kwargs={'pk': self.evento_cancelado.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404, "No debe permitir acceso a evento Cancelado.")

    # --- Casos de Prueba de Seguridad (Redirección por Rol) ---

    def test_cp05_redireccion_asistente_logueado(self):
        """Prueba CA05: El Asistente logueado es redirigido a su dashboard."""
        
        # Simular la sesión de Asistente (requerida por @visitor_required)
        # Nota: La forma de simular el logueo puede variar. 
        # Si estás usando sesiones personalizadas, la línea es correcta. 
        # Si usas Django auth por defecto, usa self.client.login().
        session = self.client.session
        session['asistente_id'] = self.asistente_perfil.pk
        session.save()
        
        url = reverse('ver_info_evento_vis', kwargs={'pk': self.evento_publicado.pk})
        response = self.client.get(url, follow=False)
        
        self.assertRedirects(
            response, 
            reverse('dashboard_asistente'), 
            status_code=302, 
            msg_prefix="Debe redirigir al dashboard de Asistente."
        )

    def test_cp06_redireccion_admin_logueado(self):
        """Prueba CA05: El Administrador de Evento logueado es redirigido a su dashboard."""
        
        # Simular la sesión de Administrador de Evento
        session = self.client.session
        session['admin_id'] = self.admin_perfil.pk
        session.save()
        
        url = reverse('ver_info_evento_vis', kwargs={'pk': self.evento_publicado.pk})
        response = self.client.get(url, follow=False)
        
        self.assertRedirects(
            response, 
            reverse('dashboard_admin'), 
            status_code=302, 
            msg_prefix="Debe redirigir al dashboard de Administrador de Evento."
        )