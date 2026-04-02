from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    모든 ORM 모델이 공통으로 상속하는 SQLAlchemy Declarative Base입니다.
    테이블 메타데이터를 한 곳에 모아 migration과 model import 경계를 단순하게 유지합니다.
    """

    pass
