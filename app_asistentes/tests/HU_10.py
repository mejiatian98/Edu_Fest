""" Como Asistente quiero Cancelar mi inscripción a un evento para 
Liberar mi cupo y que pueda ser utilizado por otra persona
"""






from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from io import BytesIO 
import random # Importar módulo random

# Asegúrate de importar todos tus modelos necesarios
from app_usuarios.models import Usuario, Asistente, AdministradorEvento, Participante
from app_admin_eventos.models import Evento
from app_asistentes.models import AsistenteEvento

# Simulación del decorador (reemplaza con tu importación real)
def asistente_required(view_func):
    """Simula el decorador de rol requerido, asume que está en tu vista."""
    return view_func

class AsistenteCancelacionTests(TestCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Generar un ID base aleatorio y grande para evitar colisiones
        # Esto es la solución final para el IntegrityError con MySQL/Django
        base_id = random.randint(10000, 99999)
        
        # Archivo simulado para campos FileField/ImageField
        simple_file = BytesIO(b"file content")
        simple_file.name = 'test_file.txt'
        cls.simple_file = simple_file

        # 1. Configuración de Usuarios y Roles (Usando IDs dinámicos)
        cls.admin_evento_user = Usuario.objects.create_user(
            id=base_id, # <<--- ID BASE DINÁMICO
            username='adm_eve_test', email='adm_eve_test@test.com', 
            password='password123', rol=Usuario.Roles.ADMIN_EVENTO
        )
        cls.asistente_user = Usuario.objects.create_user(
            id=base_id + 1, # <<--- ID SECUENCIAL DINÁMICO
            username='asis_test', email='asis_test@test.com', 
            password='password123', rol=Usuario.Roles.ASISTENTE
        )
        cls.participante_user = Usuario.objects.create_user(
            id=base_id + 2, # <<--- ID SECUENCIAL DINÁMICO
            username='part_test', email='part_test@test.com', 
            password='password123', rol=Usuario.Roles.PARTICIPANTE
        )
        
        # Crear los objetos de rol correspondientes
        # El AdministradorEvento se crea con el usuario=cls.admin_evento_user.id = base_id
        cls.admin_evento = AdministradorEvento.objects.create(usuario=cls.admin_evento_user)
        cls.asistente = Asistente.objects.create(usuario=cls.asistente_user)
        cls.participante = Participante.objects.create(usuario=cls.participante_user)

        
        # 2. Configuración de Eventos (Creados una sola vez)
        cls.evento_activo = Evento.objects.create(
            eve_nombre='Evento Activo', eve_fecha_inicio=date.today() + timedelta(days=10), 
            eve_fecha_fin=date.today() + timedelta(days=12), eve_estado='Publicado', 
            eve_administrador_fk=cls.admin_evento, eve_tienecosto='NO', eve_capacidad=100,
            eve_programacion=cls.simple_file, eve_imagen=cls.simple_file, 
            eve_descripcion="Desc", eve_ciudad="Ciudad", eve_lugar="Lugar"
        )
        
        # Evento Finalizado (para CP-10.2)
        cls.evento_finalizado = Evento.objects.create(
            eve_nombre='Evento Finalizado', eve_fecha_inicio=date.today() - timedelta(days=20), 
            eve_fecha_fin=date.today() - timedelta(days=18), eve_estado='Finalizado', 
            eve_administrador_fk=cls.admin_evento, eve_tienecosto='NO', eve_capacidad=100,
            eve_programacion=cls.simple_file, eve_imagen=cls.simple_file,
            eve_descripcion="Desc", eve_ciudad="Ciudad", eve_lugar="Lugar"
        )
        
        # Configuración de URLs (asumiendo que 'cancelar_inscripcion_asistente' existe)
        cls.url_cancelacion_activa = reverse('cancelar_inscripcion_asistente', args=[cls.evento_activo.pk])
        cls.url_cancelacion_finalizado = reverse('cancelar_inscripcion_asistente', args=[cls.evento_finalizado.pk])
        
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def setUp(self):
        # 3. Configuración de Inscripciones (se re-crean para cada test)
        # Limpiamos inscripciones de pruebas anteriores para un estado limpio
        AsistenteEvento.objects.filter(asi_eve_asistente_fk=self.asistente).delete()
        
        # Inscripción Activa (para CP-10.1 y CP-10.3)
        self.inscripcion_activa = AsistenteEvento.objects.create(
            asi_eve_asistente_fk=self.asistente, 
            asi_eve_evento_fk=self.evento_activo, 
            asi_eve_fecha_hora=timezone.now(), 
            asi_eve_estado='Aprobado',
            asi_eve_soporte=self.simple_file, asi_eve_qr=self.simple_file,
            asi_eve_clave='CLAVE123'
        )

        # Inscripción para Evento Finalizado (para CP-10.2)
        self.inscripcion_finalizada = AsistenteEvento.objects.create(
            asi_eve_asistente_fk=self.asistente, 
            asi_eve_evento_fk=self.evento_finalizado, 
            asi_eve_fecha_hora=timezone.now(), 
            asi_eve_estado='Aprobado',
            asi_eve_soporte=self.simple_file, asi_eve_qr=self.simple_file,
            asi_eve_clave='CLAVE456'
        )
        
        # Inicializar el cliente para cada test
        self.client = Client()

    # --- Tests de la Historia de Usuario HU-10 ---

    # CP-10.1: Cancelación exitosa de inscripción activa.
    def test_cancelacion_exitosa_inscripcion_activa(self):
        """ ✅ Verifica que un Asistente pueda cancelar su inscripción a un evento activo. """
        
        capacidad_inicial = self.evento_activo.eve_capacidad
        self.client.force_login(self.asistente_user)
        
        response = self.client.post(self.url_cancelacion_activa, follow=True) 
        
        # 1. Verificar la redirección exitosa
        self.assertEqual(response.status_code, 200) 

        # 2. Verificar el cambio de estado en la base de datos (CA-10.2)
        self.inscripcion_activa.refresh_from_db()
        self.assertEqual(self.inscripcion_activa.asi_eve_estado, 'Cancelado', "El estado de la inscripción debe ser 'Cancelado'")
        
        # 3. Verificar liberación de cupo
        self.evento_activo.refresh_from_db()
        self.assertEqual(self.evento_activo.eve_capacidad, capacidad_inicial + 1, "El cupo debe aumentar en 1")
        
        # 4. Verificar mensaje de éxito (CA-10.4)
        self.assertContains(response, "Has cancelado exitosamente tu inscripción", status_code=200)

    # CP-10.2: Intento de cancelación en un evento finalizado.
    def test_no_cancelacion_evento_finalizado(self):
        """ 🚫 Verifica que no se pueda cancelar la inscripción a un evento cuya fecha de fin ya pasó. """
        
        self.client.force_login(self.asistente_user)
        estado_inicial = self.inscripcion_finalizada.asi_eve_estado
        
        response = self.client.post(self.url_cancelacion_finalizado, follow=True)
        
        # 1. Verificar denegación (CA-10.1)
        self.assertEqual(response.status_code, 200) # Asume redirección
        self.assertContains(response, "no puedes cancelar una inscripción a un evento que ya finalizó", status_code=200)
        
        # 2. Verificar que el estado en DB NO cambió
        self.inscripcion_finalizada.refresh_from_db()
        self.assertEqual(self.inscripcion_finalizada.asi_eve_estado, estado_inicial, "El estado de la inscripción no debe cambiar.")

    # CP-10.3: Acceso no autorizado (Usuario no Asistente).
    def test_acceso_denegado_rol_incorrecto(self):
        """ 🔒 Verifica que solo el rol Asistente pueda usar el endpoint. """
        
        # Roles que no deberían tener acceso: Participante y Admin
        roles_incorrectos = [self.participante_user, self.admin_evento_user]

        for user in roles_incorrectos:
            with self.subTest(rol=user.rol):
                self.client.force_login(user)
                response = self.client.post(self.url_cancelacion_activa)
                
                # Se espera 403 Forbidden si el decorador lo aplica, o 302/200 si redirige.
                # Para mayor robustez en entornos reales, debes verificar que la inscripción NO cambie.
                self.assertNotEqual(response.status_code, 200, f"Rol {user.rol} no debe acceder con status 200 sin error aparente.")
                
                # Verificar que la inscripción no haya sido modificada
                self.inscripcion_activa.refresh_from_db()
                self.assertEqual(self.inscripcion_activa.asi_eve_estado, 'Aprobado', "El estado no debe cambiar por acceso no autorizado.")

    # CP-10.4: Intento de cancelación sin inscripción activa.
    def test_cancelacion_no_inscrito(self):
        """ 🛑 Verifica el manejo cuando un Asistente intenta cancelar un evento al que no está inscrito. """
        
        # Evento creado para la prueba
        evento_sin_inscripcion = Evento.objects.create(
            eve_nombre='Evento Sin Inscripción', eve_fecha_inicio=date.today() + timedelta(days=20), 
            eve_fecha_fin=date.today() + timedelta(days=22), eve_estado='Publicado', 
            eve_administrador_fk=self.admin_evento, eve_tienecosto='NO', eve_capacidad=100,
            eve_programacion=self.simple_file, eve_imagen=self.simple_file, 
            eve_descripcion="Desc", eve_ciudad="Ciudad", eve_lugar="Lugar"
        )
        url_no_inscrito = reverse('cancelar_inscripcion_asistente', args=[evento_sin_inscripcion.pk])

        self.client.force_login(self.asistente_user)
        
        response = self.client.post(url_no_inscrito, follow=True)
        
        # 1. Verificar la redirección al dashboard con mensaje de error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No tienes una inscripción activa para este evento", status_code=200)
        
        # 2. Verificar que otras inscripciones activas siguen igual
        self.inscripcion_activa.refresh_from_db()
        self.assertEqual(self.inscripcion_activa.asi_eve_estado, 'Aprobado', "El estado de otras inscripciones no debe cambiar.")