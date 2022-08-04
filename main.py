import pygit2
from ruamel import yaml
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from helper import *


class FieldValue(BaseModel):
    file: str
    values: Dict[str, Any]


class UpdateYamlRequest(BaseModel):
    repository: str
    field_values: List[FieldValue]


app = FastAPI()


@app.exception_handler(Exception)
async def validation_exception_handler(request, err):
    base_error_message = f"Failed to execute: {request.method}: {request.url}"
    # Change here to LOGGER
    return JSONResponse(status_code=400, content={"detail": f"{err}"})


@app.post("/yaml_update")
async def update_yaml(update_req: UpdateYamlRequest):
    for v in update_req.field_values:
        try:
            with open(v.file, "r") as fr:
                content = yaml.round_trip_load(fr, preserve_quotes=True)
                for k, val in v.values.items():
                    print(k)
                    update_yaml_value(content, k, val)
            with open(v.file, "w") as fw:
                yml = yaml.YAML()
                yml.indent(mapping=2, sequence=4, offset=2)
                yml.dump(content, stream=fw, transform=append_hyphen)
        except Exception as e:
            raise e

    return {"detail": "ok"}
