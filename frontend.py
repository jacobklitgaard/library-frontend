import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv("client.env")

BASE = "http://127.0.0.1:5001"
client = httpx.Client(
    base_url=BASE,
    headers={"X-API-Key": os.environ["LIBRARY_API_KEY"]},
    timeout=5.0,
)


def api(method: str, path: str, **kwargs) -> httpx.Response | None:
    """Ét sted til alle kald og alle fejl. Returnerer None, hvis noget gik galt."""
    try:
        r = client.request(method, path, **kwargs)
        r.raise_for_status()
        return r
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        try:
            message = e.response.json()["error"]
        except (ValueError, KeyError):
            message = e.response.text[:200] or "(tom body)"
        if status == 401:
            st.error("Forkert eller manglende API-nøgle (401)")
        elif status == 404:
            st.error(f"Findes ikke (404): {message}")
        elif status == 400:
            st.error(f"Ugyldig forespørgsel (400): {message}")
        else:
            st.error(f"Serveren svarede {status}: {message}")
    except httpx.ConnectError:
        st.error("Kan ikke nå API'et. Kører serveren?")
    except httpx.TimeoutException:
        st.error("API'et svarede ikke i tide.")
    return None


st.title("Bibliotek")

# --- Tilføj en bog (i sidebaren, men køres før listen hentes) ---
with st.sidebar:
    st.header("Tilføj bog")
    with st.form("add_book", clear_on_submit=True):
        title = st.text_input("Titel")
        author = st.text_input("Forfatter")
        submitted = st.form_submit_button("Tilføj")
    if submitted:
        body = {"title": title}
        if author:
            body["author"] = author
        if api("POST", "/books", json=body) is not None:
            st.success(f"'{title}' er tilføjet")

# --- Vis bøgerne ---
r = api("GET", "/books")
books = r.json() if r is not None else []

for book in books:
    col_title, col_status, col_action = st.columns([3, 2, 2])
    col_title.write(f"**{book['title']}** – {book['author'] or 'ukendt forfatter'}")

    if book["borrower"] is None:
        borrower = col_status.text_input(
            "Låner", key=f"borrower_{book['id']}",
            label_visibility="collapsed", placeholder="Navn på låner",
        )
        if col_action.button("Lån ud", key=f"loan_{book['id']}"):
            if api("POST", f"/books/{book['id']}/loan", json={"borrower": borrower}) is not None:
                st.rerun()
    else:
        col_status.write(f"Udlånt til **{book['borrower']}**")
        if col_action.button("Aflever", key=f"return_{book['id']}"):
            if api("POST", f"/books/{book['id']}/return") is not None:
                st.rerun()