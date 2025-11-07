from .models import GiamKhao

def judge_info(request):
    """Add judge login and role info to every template context.

    Sets:
      - is_logged_in: bool
      - current_judge_email: str or None
      - current_judge_role: 'ADMIN'|'JUDGE'|None
      - is_admin: bool
      - is_judge: bool
    """
    info = {
        'is_logged_in': False,
        'current_judge_email': None,
        'current_judge_role': None,
        'is_admin': False,
        'is_judge': False,
    }

    pk = request.session.get('judge_pk')
    email = request.session.get('judge_email')
    if pk or email:
        info['is_logged_in'] = True
        info['current_judge_email'] = email
        try:
            if pk:
                g = GiamKhao.objects.filter(pk=pk).first()
            else:
                g = GiamKhao.objects.filter(email__iexact=email).first()
            if g:
                info['current_judge_role'] = getattr(g, 'role', None)
                info['is_admin'] = (g.role == 'ADMIN')
                info['is_judge'] = (g.role == 'JUDGE')
        except Exception:
            # swallow DB errors to avoid breaking rendering
            pass

    return info
