from .models import ParticipanteEvento
from app_usuarios.models import Participante

def obtener_proyectos_por_evento(evento):
    """
    Obtiene todos los proyectos (individuales y grupales) de un evento
    Retorna solo los líderes de proyecto (no duplica miembros)
    """
    return ParticipanteEvento.objects.filter(
        par_eve_evento_fk=evento,
        par_eve_proyecto_principal__isnull=True  # Solo líderes
    )

def obtener_miembros_proyecto(participante_evento):
    """
    Obtiene todos los miembros de un proyecto incluyendo el líder
    """
    if participante_evento.par_eve_proyecto_principal:
        # Si es miembro, obtener desde el proyecto principal
        return participante_evento.par_eve_proyecto_principal.get_todos_miembros_proyecto()
    else:
        # Si es líder, obtener todos los miembros
        return participante_evento.get_todos_miembros_proyecto()

def es_lider_proyecto(participante_evento):
    """
    Verifica si un participante es líder de proyecto
    """
    return participante_evento.par_eve_proyecto_principal is None

def obtener_proyecto_principal(participante_evento):
    """
    Obtiene el proyecto principal (líder) de un participante
    """
    if participante_evento.par_eve_proyecto_principal:
        return participante_evento.par_eve_proyecto_principal
    else:
        return participante_evento  # Es el líder

def contar_miembros_proyecto(participante_evento):
    """
    Cuenta el total de miembros de un proyecto (incluyendo líder)
    """
    proyecto_principal = obtener_proyecto_principal(participante_evento)
    return 1 + proyecto_principal.miembros_proyecto.count()  # 1 (líder) + miembros

def obtener_participantes_por_codigo_proyecto(codigo_proyecto, evento):
    """
    Obtiene todos los participantes de un proyecto por código
    """
    return ParticipanteEvento.objects.filter(
        par_eve_codigo_proyecto=codigo_proyecto,
        par_eve_evento_fk=evento
    )

def obtener_estadisticas_evento(evento):
    """
    Obtiene estadísticas de participación de un evento
    """
    proyectos_individuales = ParticipanteEvento.objects.filter(
        par_eve_evento_fk=evento,
        par_eve_es_grupo=False
    ).count()
    
    proyectos_grupales = ParticipanteEvento.objects.filter(
        par_eve_evento_fk=evento,
        par_eve_es_grupo=True,
        par_eve_proyecto_principal__isnull=True  # Solo líderes
    ).count()
    
    total_participantes = ParticipanteEvento.objects.filter(
        par_eve_evento_fk=evento
    ).count()
    
    return {
        'proyectos_individuales': proyectos_individuales,
        'proyectos_grupales': proyectos_grupales,
        'total_proyectos': proyectos_individuales + proyectos_grupales,
        'total_participantes': total_participantes
    }