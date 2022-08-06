import pygit2
from ruamel import yaml
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from helper import *
import os
import random
import string
import shutil


class FieldValue(BaseModel):
    file: str
    values: Dict[str, Any]


class UpdateYamlRequest(BaseModel):
    repository: str
    branch: str
    field_values: List[FieldValue]


git_user = os.environ["GIT_USER"]
git_token = os.environ["GIT_TOKEN"]


app = FastAPI()


@app.exception_handler(Exception)
async def validation_exception_handler(request, err):
    base_error_message = f"Failed to execute: {request.method}: {request.url}"
    # Change here to LOGGER
    return JSONResponse(status_code=400, content={"detail": f"{err}"})


@app.post("/yaml_update")
async def update_yaml(update_req: UpdateYamlRequest):
    branch = update_req.branch
    repo_name = "".join(random.choices(string.ascii_lowercase, k=16))
    git_url = f"https://{git_user}:{git_token}@{update_req.repository}"
    repo = pygit2.clone_repository(git_url, repo_name, checkout_branch=branch)

    for v in update_req.field_values:
        try:
            with open(f"{repo_name}/{v.file}", "r") as fr:
                content = yaml.round_trip_load(fr, preserve_quotes=True)
                for k, val in v.values.items():
                    if not update_yaml_value(content, k, val):
                        raise Exception(f"path {k} doesn't exist in file {v.file}")
            with open(f"{repo_name}/{v.file}", "w") as fw:
                yml = yaml.YAML()
                yml.indent(mapping=2, sequence=4, offset=2)
                yml.dump(content, stream=fw, transform=append_hyphen)
        except Exception as e:
            shutil.rmtree(repo_name, ignore_errors=True)
            raise e

    status: Dict[str, int] = repo.status()
    if bool(status):
        try:
            index = repo.index
            index.add_all()
            index.write()
            author = pygit2.Signature("bot", "bot@cinnamon.is")
            message = "deliver new release"
            tree = index.write_tree()
            parents = [repo.head.target]
            repo.create_commit("HEAD", author, author, message, tree, parents)

            remote = repo.remotes["origin"]
            remote.push([f"refs/heads/{branch}"])
        except Exception as e:
            shutil.rmtree(repo_name, ignore_errors=True)
            raise e

    shutil.rmtree(repo_name, ignore_errors=True)
    return {"detail": "ok"}
