import pygit2
from ruamel import yaml
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import random
import string
import shutil
import glob
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class FieldValue(BaseModel):
    file: str
    values: Dict[str, Any]


class UpdateYamlRequest(BaseModel):
    git_server: str = "github.com"
    repo_url: str
    # repository: str
    path: str
    branch: str = "master"
    image_urls: List[str] = []
    field_values: List[FieldValue] = []
    deploy_type: str = "helm"
    created_by: str


git_user = os.environ["GIT_USER"]
git_token = os.environ["GIT_TOKEN"]
git_email = os.environ["GIT_EMAIL"]


app = FastAPI()


def get_value(s: str) -> Any:
    if s.isnumeric():
        return int(s)
    return s


# update yaml content based ok data path, EX: image.tag, ingress.hosts.[0].host


def update_yaml_value(content: dict, path: str, data: str) -> bool:
    layers = path.split(".")
    value = content

    for i in range(len(layers)):
        s = get_value(layers[i])
        if s == None:
            return False

        if i < len(layers) - 1:
            if isinstance(s, str):
                value = value.get(s)
            else:
                value = value[s]

            if value == None:
                return False

            continue

        if value.get(s) == None:
            return False
        value[s] = data

    return True


# ["repo_x:tag_a", "repo_y:tag_b"] -> {"repo_x": "tag_a", "repo_y": "tag_b"}
def parse_imagesurl_to_dict(images_url: List[str]) -> Dict[str, str]:
    imgs = {}
    for repo in images_url:
        i = repo.split(":")[0]
        tag = repo.split(":")[1]
        imgs[i] = tag

    return imgs


# check if repoimage exist in yaml file before take action
def check_img_exist_file(filename: str, imgs: Dict[str, str]) -> bool:
    with open(filename, "r") as fr:
        data = fr.read()
        for k in imgs:
            if k in data:
                return True

    return False


# update image tag for docker compose deployment
def update_image_docker_compose_tag(filename: str, imgs: Dict[str, str]):
    updated = 0

    with open(filename, "r") as fr:
        content = yaml.round_trip_load(fr, preserve_quotes=True)

        for i, t in imgs.items():
            if content.get("services") is None:
                continue
            else:
                for service in content["services"]:
                    if content.get("services") is None:
                        continue
                    elif i in content["services"][service]["image"]:
                        image_str = str(content["services"][service]["image"]).split(
                            ":"
                        )
                        content["services"][service]["image"] = (
                            str(image_str[0]) + ":" + str(t)
                        )
                        updated += 1
                        logger.info(
                            f'Update image {content["services"][service]["image"]} in file {filename}'
                        )
                    else:
                        continue

    if updated > 0:
        with open(filename, "w") as fw:
            yml = yaml.YAML()
            yml.indent(mapping=2, sequence=4, offset=2)
            yml.dump(content, stream=fw, transform=append_hyphen)
    else:
        pass


# check if repo exist in yaml file, then update image tag
def update_helm_image_tag(filename: str, imgs: Dict[str, str]):
    updated = 0

    with open(filename, "r") as fr:
        content = yaml.round_trip_load(fr, preserve_quotes=True)
        for i, t in imgs.items():
            if i in content["image"]["repository"]:
                content["image"]["tag"] = t
                updated += 1
                logger.info(
                    f'Update image {str(content["image"]["repository"])}:{content["image"]["tag"]} in: filename'
                )
            if "sidecarContainers" in content:
                for sc in content["sidecarContainers"]:
                    if i in sc["image"]:
                        sc["image"] = f"{i}:{t}"
                        updated += 1
                        logger.info(
                            f'Update image {str(content["sidecarContainers"])}:{str(content["image"]["tag"])} in: filename'
                        )

    if updated > 0:
        with open(filename, "w") as fw:
            yml = yaml.YAML()
            yml.indent(mapping=2, sequence=4, offset=2)
            yml.dump(content, stream=fw, transform=append_hyphen)


def append_hyphen(yaml: str) -> str:
    return "---\n" + yaml


# list all yaml file in specific directory path
def list_yaml_file(path: str) -> List[str]:
    files = []
    check_files = glob.glob(f"{path}/**/*", recursive=True) + glob.glob(
        f"{path}/**/.*", recursive=True
    )

    for f in check_files:
        fn, suf = os.path.splitext(f)
        if suf == ".yml" or suf == ".yaml":
            files.append(f)

    return files


@app.exception_handler(Exception)
async def validation_exception_handler(request, err):
    # base_error_message = f"Failed to execute: {request.method}: {request.url}"
    # Change here to LOGGER
    return JSONResponse(status_code=400, content={"detail": f"{err}"})


# list all yaml in dir path, then find and update image tag if image repo exist
@app.post("/release_image")
async def update_yaml(update_req: UpdateYamlRequest):
    branch = update_req.branch
    repo_name = "".join(random.choices(string.ascii_lowercase, k=16))
    git_url = (
        f"https://{git_user}:{git_token}@{update_req.git_server}/{update_req.repo_url}"
    )
    repo = pygit2.clone_repository(git_url, repo_name, checkout_branch=branch)

    # check container image exist in list
    updated = 0
    if len(update_req.image_urls) > 0:
        imgs = parse_imagesurl_to_dict(update_req.image_urls)
        files = list_yaml_file(repo_name + "/" + update_req.path)
        logger.info(f"Updating workloads {update_req.repo_url} path: {update_req.path}")

        for f in files:
            if check_img_exist_file(f, imgs) and update_req.deploy_type == "helm":
                try:
                    update_helm_image_tag(f, imgs)
                    updated += 1
                except Exception as e:
                    shutil.rmtree(repo_name, ignore_errors=True)
                    raise e
            elif check_img_exist_file(f, imgs) and update_req.deploy_type == "compose":
                try:
                    update_image_docker_compose_tag(f, imgs)
                    updated += 1
                except Exception as e:
                    shutil.rmtree(repo_name, ignore_errors=True)
                    raise e
            else:
                continue

    for v in update_req.field_values:
        try:
            with open(f"{repo_name}/{v.file}", "r") as fr:
                content = yaml.round_trip_load(fr, preserve_quotes=True)
                for k, val in v.values.items():
                    if not update_yaml_value(content, k, val):
                        raise Exception(f"path {k} doesn't exist in file {v.file}")
                    updated += 1
            with open(f"{repo_name}/{v.file}", "w") as fw:
                yml = yaml.YAML()
                yml.indent(mapping=2, sequence=4, offset=2)
                yml.dump(content, stream=fw, transform=append_hyphen)
        except Exception as e:
            shutil.rmtree(repo_name, ignore_errors=True)
            raise e

    if updated == 0:
        shutil.rmtree(repo_name, ignore_errors=True)
        raise ValueError("Nothing to update")

    status: Dict[str, int] = repo.status()
    if bool(status):
        try:
            index = repo.index
            index.add_all()
            index.write()
            commiter = pygit2.Signature(git_user, git_email)
            author = update_req.created_by
            message = (
                f"{author} auto released {','.join(map(str, update_req.image_urls))}"
            )
            tree = index.write_tree()
            parents = [repo.head.target]
            repo.create_commit("HEAD", commiter, commiter, message, tree, parents)

            remote = repo.remotes["origin"]
            remote.push([f"refs/heads/{branch}"])
            logger.info(message)
        except Exception as e:
            shutil.rmtree(repo_name, ignore_errors=True)
            raise e

    shutil.rmtree(repo_name, ignore_errors=True)
    return {
        "detail": f"{author} update {','.join(map(str, update_req.image_urls))} to {update_req.repo_url} path: {update_req.path} success"
    }
