"""
Cryptoverse thread influencers
==============================

"""

from algorithms.utils import param
from collections import defaultdict

ROOT_AUTHOR_QUERY = """
MATCH (rootAuthor)-[:AUTHORED]->(root:Claim { id: {id} })-[:IN]->(package)
OPTIONAL MATCH (reply)-[:ABOUT]->(root)
RETURN
    rootAuthor.id AS root_author,
    package.timestamp AS created_at,
    count(reply) AS replies_count
"""

THREAD_AUTHORS_QUERY = """
MATCH (root:Claim { id: {id} })
OPTIONAL MATCH (replyAuthor)-[:AUTHORED]->(reply)-[:ABOUT]->(root)
OPTIONAL MATCH (likeAuthor)-[:AUTHORED]->(like)-[:TARGET]->(reply)
OPTIONAL MATCH (replyReplyAuthor)-[:AUTHORED]->(replyReply)-[:ABOUT]->(reply)
RETURN
    reply.id AS reply_id,
    replyAuthor.id AS reply_author,
    replyAuthor.id + collect(likeAuthor.id) + collect(replyReplyAuthor.id) AS authors
"""

COUNT_TOKENS_QUERY = """
SELECT * from token_count(%(addresses)s);
"""

golden_ratio = [610, 377, 233, 144, 89, 55, 34, 21, 13, 8, 5, 3, 2, 1]

@param("id", required=True)
def run(conn_mgr, input, **params):
    row = conn_mgr.run_graph(ROOT_AUTHOR_QUERY, params).single()
    root_author = row["root_author"]
    created_at = row["created_at"]
    if not row["replies_count"]:
        return {
            "addresses": {
                root_author: 10000000,
            },
            "created_at": created_at
        }
    result = conn_mgr.run_graph(THREAD_AUTHORS_QUERY, params)
    result = [{"reply_author": x["reply_author"], "authors": set(x["authors"])} for x in result]
    authors = set()
    for r in result:
        authors |= r["authors"]
    author_power = count_tokens(conn_mgr, authors)
    for r in result:
        r["authors"] = [a for a in r["authors"] if author_power.get(a)]
    result = [r for r in result if r["authors"]]
    author_activity = defaultdict(int)
    for r in result:
        for a in r["authors"]:
            author_activity[a] += 1
    for a, p in author_power.items():
        author_power[a] /= author_activity[a]
    for r in result:
        r["power"] = sum(map(lambda a: author_power[a], r["authors"]))
    result.sort(key=lambda r: r["power"], reverse=True)
    result = result[:len(golden_ratio)]
    for r in result:
        r["authors"] = sorted([{"id": a, "power": author_power[a]} for a in r["authors"]], key=lambda a: a["power"], reverse=True)[:len(golden_ratio)]
    author_ratio = defaultdict(int)
    author_ratio[root_author] = 10000000
    s = sum(golden_ratio[:len(result)])
    for index, r in enumerate(result):
        author_ratio[r["reply_author"]] += 30000000 * golden_ratio[index] / s
        c = 60000000 * golden_ratio[index] / s
        s2 = sum(golden_ratio[:len(r["authors"])])
        for index, a in enumerate(r["authors"]):
            author_ratio[a["id"]] += c * golden_ratio[index] / s2
    return {
        "addresses": author_ratio,
        "created_at": created_at
    }


def count_tokens(conn_mgr, authors):
    result = conn_mgr.run_rdb(COUNT_TOKENS_QUERY, {"addresses": list(authors)})
    return {row["address"]: row["count"] for row in result if row["count"]}
