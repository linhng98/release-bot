# Release bot

## Usage with helm repo gitops

```
POST /release_image

{
  git_server: "github.com"
  repo_url: "argo-workload"
  path: "prod/serviceA"
  branch: "master"
  field_values: [
    {
      file: "values.yaml",
      value: {
        "image.tag": "1.1.0",
      }
    },
  ]
  created_by: "Linh Nguyen"
}
```
