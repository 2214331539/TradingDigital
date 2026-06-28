from tradedigital.platform.org.models import Enterprise


def enterprise_out(enterprise: Enterprise) -> dict:
    return {
        "id": enterprise.id,
        "name": enterprise.name,
        "code": enterprise.code,
        "status": enterprise.status,
    }

