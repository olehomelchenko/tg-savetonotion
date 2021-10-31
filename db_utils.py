import sqlalchemy as db
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.orm import Session
import logging
import os

metadata = db.MetaData()


sql_string = os.environ.get("PG_STRING")
PG_TABLE_NAME = os.getenv("PG_TABLE_NAME")
engine = db.create_engine(sql_string)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


logger = logging.getLogger(__name__)


def get_table():

    table_name = PG_TABLE_NAME

    try:
        tbl = db.Table(table_name, metadata, autoload=True, autoload_with=engine)
        logger.info(f"table exists, connecting to existing table {tbl}")
        return tbl
    except NoSuchTableError as e:
        tbl = db.Table(
            table_name,
            metadata,
            db.Column("id", db.Integer(), primary_key=True),
            db.Column(
                "created_time",
                db.TIMESTAMP,
                server_default=db.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            db.Column("notion_token", db.String(100), nullable=True),
            db.Column("notion_db", db.String(100), nullable=True),
            db.Column("tg_user_id", db.String(50), nullable=False),
        )
        metadata.create_all(engine)
        logger.info(f"created table {tbl}")
        return tbl


def get_user(uid):
    s = Session(engine)
    tbl = get_table()

    user = s.query(tbl).filter_by(tg_user_id=str(uid)).one()

    s.close()

    return user


def create_user(uid):

    tbl = get_table()

    conn = engine.connect()
    query = db.insert(tbl).values(tg_user_id=str(uid))
    ResultProxy = conn.execute(query)
    logger.info(f"Created user {ResultProxy}")
    conn.close()

def update_user(uid, **kwargs):
    tbl = get_table()
    conn = engine.connect()
    query = (
        db.update(tbl)
        .values(**kwargs)
        .where(tbl.columns.tg_user_id == str(uid))
    )
    conn.execute(query)
    conn.close()