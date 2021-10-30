import sqlalchemy as db
from sqlalchemy.exc import NoSuchTableError
import logging

metadata = db.MetaData()


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def get_table(engine, conn, table_name):

    try:
        tbl = db.Table(table_name, metadata, autoload=True, autoload_with=engine)
        logger.info("table exists, connecting to existing table")
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
        logger.info("created table")
        return tbl

