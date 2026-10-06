from sqlalchemy import (
    ColumnElement,
    CompoundSelect,
    Integer,
    Select,
    Text,
    column,
    func,
    literal,
    literal_column,
    select,
    table,
    union_all,
)

from vexicon import orm
from vexicon.models.base import Filter, Metadata
from vexicon.queries.filtering import where_condition, where_document_condition

type KeywordRow = tuple[int, str, str, Metadata | None, float]

documents_fts = table("documents_fts", column("rowid", Integer))
fts_match_target = literal_column("documents_fts", type_=Text)


def collection_id_select(name: str) -> Select[tuple[int]]:
    return select(orm.Collection.id).where(orm.Collection.name == name)


def keyword_search_select(
    collection_id: int,
    expressions: list[tuple[int, str]],
    limit: int,
    where: Filter | None = None,
    where_document: Filter | None = None,
) -> CompoundSelect[KeywordRow]:
    """Selects up to limit FTS5 matches per phrase, ranked by bm25 and tagged with the phrase index."""
    score = func.bm25(fts_match_target).label("score")
    filters: list[ColumnElement[bool]] = [orm.Document.collection_id == collection_id]
    if where is not None:
        filters.append(where_condition(where))
    if where_document is not None:
        filters.append(where_document_condition(where_document))
    members: list[Select[KeywordRow]] = []
    for index, expression in expressions:
        ranked = (
            select(
                literal(index).label("phrase_index"),
                orm.Document.chroma_id,
                orm.Document.document,
                orm.Document.meta,
                score,
            )
            .select_from(orm.Document)
            .join(documents_fts, documents_fts.c.rowid == orm.Document.id)
            .where(fts_match_target.op("MATCH")(expression), *filters)
            .order_by(score)
            .limit(limit)
            .subquery()
        )
        members.append(select(ranked))
    return union_all(*members).order_by("phrase_index", "score")
