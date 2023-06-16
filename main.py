import os
import sqlite3 as sl
import plexapi
from db_conn import Movie_DB, Show_DB, ENGINE
from sqlalchemy import select
from sqlalchemy.orm import Session
import json
import copy
import requests
import yaml

os.chdir(os.path.dirname(__file__))
if not os.path.isfile('config.yml'):
    with open('config.yml', 'w') as f:
        f.write('plex url: [CHANGE ME]\n')
        f.write('plex token: [CHANGE ME]\n')
        f.write('pushbullet key: [CHANGE ME]\n')
    raise Exception("Please update the config.yml")
with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)
    if config.get('pushbullet key', '[CHANGE ME]') == '[CHANGE ME]':
        raise Exception("Please fix 'pushbullet key' in the config.yml")
    if config.get('plex token', '[CHANGE ME]') == '[CHANGE ME]':
        raise Exception("Please fix 'plex token' in the config.yml")
    if config.get('plex url', '[CHANGE ME]') == '[CHANGE ME]':
        raise Exception("Please fix 'plex url' in the config.yml")


def get_plex():
    from plexapi.server import PlexServer
    baseurl = config.get('plex url')
    token = config.get('plex token')
    plex = PlexServer(baseurl, token)
    return plex


def jsonable_obj(obj):
    new_obj = {}
    for key, val in obj.__dict__.items():
        if key[0] == '_':
            continue
        if not val:
            continue
        try:
            json.dumps(val)
            new_obj[key] = copy.copy(val)
        except:
            try:
                json.dumps(repr(val))
                new_obj[key] = copy.copy(repr(val))
            except:
                continue
            continue
    return new_obj


def do_movies(plex):
    plex_movies_keys = set()
    added = []
    removed = []
    movies = plex.library.section('Movies').all()

    with Session(ENGINE) as session:
        for plex_movie in movies:
            stmt = select(Movie_DB).where(Movie_DB.key == plex_movie.key)
            existing_movie = session.scalars(stmt).one_or_none()
            if not existing_movie:
                json_obj = jsonable_obj(plex_movie)
                new_movie = Movie_DB(
                    key=plex_movie.key,
                    title=plex_movie.title,
                    active=True,
                    is_played=plex_movie.isPlayed,
                    added_at=plex_movie.addedAt,
                    updated_at=plex_movie.updatedAt,
                    json_data=json_obj
                )
                session.add(new_movie)
                added.append(new_movie.title)
            else:
                if not existing_movie.active:
                    added.append(existing_movie.title)
                json_obj = jsonable_obj(plex_movie)
                existing_movie.title = plex_movie.title
                existing_movie.is_played = plex_movie.isPlayed
                existing_movie.added_at = plex_movie.addedAt
                existing_movie.updated_at = plex_movie.updatedAt
                existing_movie.json_data = json.loads(json.dumps(json_obj))
                existing_movie.active = True
                session.add(existing_movie)
            plex_movies_keys.add(plex_movie.key)
        session.commit()

        stmt = select(Movie_DB).where(Movie_DB.active == True)
        existing_movies = session.scalars(stmt).all()
        for existing_movie in existing_movies:
            if existing_movie.key not in plex_movies_keys:
                # Deleted
                existing_movie.active = False
                session.add(existing_movie)
                removed.append(existing_movie.title)
        session.commit()
    return added, removed


def do_shows(plex):
    plex_shows_keys = set()
    added = []
    removed = []
    shows = plex.library.section('TV Shows').all()

    with Session(ENGINE) as session:
        for plex_show in shows:
            for episode in plex_show.episodes():
                stmt = select(Show_DB).where(Show_DB.key == episode.key)
                existing = session.scalars(stmt).one_or_none()
                if not existing:
                    json_obj = jsonable_obj(episode)
                    new_movie = Show_DB(
                        key=episode.key,
                        title=f"{ episode.title }__{ episode.seasonEpisode }",
                        active=True,
                        is_played=episode.isPlayed,
                        added_at=episode.addedAt,
                        updated_at=episode.updatedAt,
                        json_data=json_obj
                    )
                    session.add(new_movie)
                    added.append(new_movie.title)
                else:
                    changed = False
                    if existing.title != episode.title:
                        changed = True
                    if existing.is_played != episode.isPlayed:
                        changed = True
                    if existing.added_at != episode.addedAt:
                        changed = True
                    if existing.updated_at != episode.updatedAt:
                        changed = True
                    if not existing.active:
                        changed = True
                        added.append(existing.title)
                    if changed:
                        json_obj = jsonable_obj(episode)
                        existing.title = episode.title
                        existing.is_played = episode.isPlayed
                        existing.added_at = episode.addedAt
                        existing.updated_at = episode.updatedAt
                        existing.json_data = json.loads(json.dumps(json_obj))
                        existing.active = True
                        session.add(existing)
                plex_shows_keys.add(episode.key)
        session.commit()

        stmt = select(Show_DB).where(Show_DB.active == True)
        existing_episodes = session.scalars(stmt).all()
        for existing in existing_episodes:
            if existing.key not in plex_shows_keys:
                # Deleted
                existing.active = False
                session.add(existing)
                removed.append(existing.title)
        session.commit()
    return added, removed


def send_pushbullet(subject, body):
    key = config.get('pushbullet key')
    data = {"type": "note",
            "title": subject,
            "body": body}

    session = requests.Session()
    session.auth = (key, "")
    session.headers.update({"Content-Type": "application/json"})
    r = session.post('https://api.pushbullet.com/v2/pushes', data=json.dumps(data))
    if r.status_code != requests.codes.ok:
        raise Exception(f"Error calling pushbullet:{r.text}")
    return


def main():
    plex = get_plex()
    print("Doing Shows...")
    added_shows, removed_shows = do_shows(plex)
    print("Doing Movies...")
    added_movies, removed_movies = do_movies(plex)
    addedStr = ''
    if added_movies:
        addedStr += "New Movies:\n"
        for movie in added_movies:
            addedStr += f"* { movie }\n"
    if added_shows:
        addedStr += "New Episodes:\n"
        for episode in added_shows:
            addedStr += f"* { episode }\n"
    removedStr = ''
    if removed_movies:
        removedStr += "Removed Movies:\n"
        for movie in removed_movies:
            removedStr += f"* { movie }\n"
    if removed_shows:
        removedStr += "Removed Episodes:\n"
        for episode in removed_shows:
            removedStr += f"* { episode }\n"
    if addedStr:
        send_pushbullet('New Content', addedStr)
        print(addedStr)
    if removedStr:
        send_pushbullet('Removed Content', addedStr)
        print(removedStr)
    return


if __name__ == '__main__':
    print("Calling main...")
    main()
    print("Done.")
    # movies = plex.library.section('Movies').all()
    # shows = plex.library.section('TV Shows').all()
    print()
