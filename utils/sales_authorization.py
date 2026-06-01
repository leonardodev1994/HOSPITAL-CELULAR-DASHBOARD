from utils.auth import verify_password
from utils.permissions import PROFILE_ADMIN, PROFILE_MANAGER, normalize_profile
from utils.quiosques import user_quiosque_id


def can_directly_change_sale(user, sale_quiosque_id):
    profile = normalize_profile((user or {}).get("perfil"))
    if profile == PROFILE_ADMIN:
        return True
    if profile == PROFILE_MANAGER:
        return user_quiosque_id(user) == int(sale_quiosque_id or 0)
    return False


def find_authorizer(conn, identifier):
    identifier = str(identifier or "").strip()
    if not identifier:
        return None

    cursor = conn.cursor()
    return cursor.execute("""
    SELECT
        id,
        nome,
        usuario,
        senha_hash,
        senha_salt,
        perfil,
        ativo,
        quiosque_id,
        acesso_todos_quiosques
    FROM usuarios
    WHERE ativo = 1
      AND (LOWER(usuario) = LOWER(?) OR LOWER(nome) = LOWER(?))
    LIMIT 1
    """, (identifier, identifier)).fetchone()


def validate_sale_authorization(conn, identifier, password, sale_quiosque_id):
    user = find_authorizer(conn, identifier)
    if not user:
        return None, "Usuário autorizador não encontrado."

    (
        user_id,
        nome,
        usuario,
        senha_hash,
        senha_salt,
        perfil,
        ativo,
        quiosque_id,
        acesso_todos_quiosques,
    ) = user

    if not ativo or not verify_password(password or "", senha_salt, senha_hash):
        return None, "Usuário ou senha de autorização inválidos."

    profile = normalize_profile(perfil)
    authorizer = {
        "id": user_id,
        "nome": nome,
        "usuario": usuario,
        "perfil": profile,
        "quiosque_id": int(quiosque_id or 1),
        "acesso_todos_quiosques": int(acesso_todos_quiosques or 0),
    }

    if profile == PROFILE_ADMIN:
        return authorizer, ""

    if profile == PROFILE_MANAGER and int(quiosque_id or 0) == int(sale_quiosque_id or 0):
        return authorizer, ""

    return None, "A autorização precisa ser de um admin ou gerente do mesmo quiosque."
