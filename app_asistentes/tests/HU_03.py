""" Como visitante web (asistente) quiero Acceder a 
información detallada sobre los eventos de mi interés para 
Tener mayor claridad sobre mi posibilidad e interés de asistir"""



from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from app_admin_eventos.models import Evento
from app_usuarios.models import Usuario, Asistente, AdministradorEvento 
from django.core.files.uploadedfile import SimpleUploadedFile
import time 

# Asumiendo que 'ver_info_evento' es el nombre de la URL para EventoDetailView
LOGIN_URL = '/login/' 

class EventoDetailViewTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # 1. Configuración de Usuarios
        unique_id = int(time.time() * 1000)

        # 1.1 Usuario Administrador
        cls.user_admin, _ = Usuario.objects.get_or_create(
            username=f'admin_test_{unique_id}', 
            defaults={
                'email': f'admin{unique_id}@event.com', 
                'password': 'password123', 
                'rol': Usuario.Roles.ADMIN_EVENTO,
                'is_staff': True
            }
        )
        cls.admin, _ = AdministradorEvento.objects.get_or_create(usuario=cls.user_admin)

        # 1.2 Usuario Asistente
        cls.user_asistente, _ = Usuario.objects.get_or_create(
            username=f'asistente_test_{unique_id}', 
            defaults={
                'email': f'asistente{unique_id}@event.com',
                'password': 'password123', 
                'rol': Usuario.Roles.ASISTENTE
            }
        )
        cls.asistente, _ = Asistente.objects.get_or_create(usuario=cls.user_asistente)

        # 2. Archivos dummy
        cls.dummy_image = SimpleUploadedFile("test_img.png", b"file_content", content_type="image/png")
        cls.dummy_pdf = SimpleUploadedFile("test_prog.pdf", b"pdf_content", content_type="application/pdf")
        
        # 3. Crear Eventos de Prueba
        cls.manana = timezone.now().date() + timedelta(days=1)
        
        # Evento 1: Publicado y Accesible (CA-2.1, CA-2.2, CA-2.3)
        cls.evento_publicado = Evento.objects.create(
            eve_nombre="Congreso de Bioinformática", 
            eve_descripcion="Detalles completos del evento.",
            eve_ciudad="Medellín",
            eve_lugar="UNAL",
            eve_fecha_inicio=cls.manana,
            eve_fecha_fin=cls.manana + timedelta(days=2),
            eve_estado="Publicado",
            eve_administrador_fk=cls.admin,
            eve_tienecosto='De pago',
            eve_capacidad=150,
            eve_programacion=cls.dummy_pdf,
            # NOTA: En tests, se simula que el archivo está subido (aunque no se guarda en disco)
            eve_imagen=SimpleUploadedFile("test_img.png", b"file_content", content_type="image/png") 
        )
        
        # Evento 2: Editando (CA-2.4)
        cls.evento_editando = Evento.objects.create(
            eve_nombre="Taller Interno", 
            eve_descripcion="Solo para admins.",
            eve_ciudad="Cali",
            eve_lugar="Sede Central",
            eve_fecha_inicio=cls.manana,
            eve_fecha_fin=cls.manana + timedelta(days=1),
            eve_estado="Editando",
            eve_administrador_fk=cls.admin,
            eve_tienecosto='Sin costo',
            eve_capacidad=10,
            eve_programacion=SimpleUploadedFile("test_prog_2.pdf", b"pdf_content", content_type="application/pdf"),
            eve_imagen=SimpleUploadedFile("test_img_2.png", b"file_content", content_type="image/png") 
        )

    def setUp(self):
        self.client = Client()
        self.url_publicado = reverse('ver_info_evento', kwargs={'pk': self.evento_publicado.pk})
        self.url_editando = reverse('ver_info_evento', kwargs={'pk': self.evento_editando.pk})
        self.url_inexistente = reverse('ver_info_evento', kwargs={'pk': 9999})
        

    # --- CP-2.1: Acceso Exitoso a Evento Publicado (CA-2.1, CA-2.3) ---
    def test_cp_2_1_acceso_exitoso_evento_publicado_autenticado(self):
        """Valida CA-2.1 y CA-2.3: Usuario ASISTENTE (logueado) accede a evento 'Publicado'."""
        
        self.client.login(username=self.user_asistente.username, password='password123')
        response = self.client.get(self.url_publicado)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['evento'], self.evento_publicado)
        self.assertContains(response, 'Congreso de Bioinformática')
        # Verificar la aserción de conteo para asegurar que los datos del evento están en el cuerpo
        self.assertContains(response, self.evento_publicado.eve_descripcion, count=1)


    # --- CP-2.2: Acceso Público (Visitante No Autenticado) (CA-2.2) ---
    def test_cp_2_2_acceso_publico_visitante_web(self):
        """
        AJUSTE: Confirma que la vista es pública (Status 200) y que el contenido del evento 'Publicado' es visible.
        """
        
        # ACT: Intentar acceder como VISITANTE WEB (no logueado)
        response = self.client.get(self.url_publicado)
        
        # ASSERT: Esperamos 200 (Acceso público)
        self.assertEqual(response.status_code, 200)
        
        # CORRECCIÓN: Aserción ajustada para contar las ocurrencias (título H2 y alt de imagen)
        self.assertContains(response, 'Congreso de Bioinformática', count=2, 
                            msg_prefix="El contenido del evento Publicado no fue encontrado o la cuenta no coincide.")
        

    # --- CP-2.3: Acceso Negado a Evento No Público (Editando) (CA-2.4) ---
    def test_cp_2_3_acceso_negado_evento_editando(self):
        """
        AJUSTE: Valida CA-2.4: El usuario autenticado (ASISTENTE) NO debe acceder a un evento en estado 'Editando'. 
        La vista ahora retorna correctamente 404 (Not Found).
        """
        
        self.client.login(username=self.user_asistente.username, password='password123')
        
        response = self.client.get(self.url_editando)
        
        # CORRECCIÓN: Se esperaba 200 (vulnerabilidad), pero la vista corregida retorna 404. 
        # Ajustamos el test para esperar el comportamiento de seguridad deseado.
        self.assertEqual(response.status_code, 404, 
                         "Error: La vista expone eventos en estado 'Editando' (debería ser 404/403).")

    # --- CP-2.4: Evento Inexistente (CA-2.5) ---
    def test_cp_2_4_evento_inexistente(self):
        """Valida CA-2.5: Intento de acceso a un PK que no existe."""
        
        self.client.login(username=self.user_asistente.username, password='password123')
        
        response = self.client.get(self.url_inexistente)
        
        self.assertEqual(response.status_code, 404)