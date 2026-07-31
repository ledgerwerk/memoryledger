# Deprecations

The canonical command names are documented in [CLI reference](cli). These
aliases remain for compatibility and are hidden from normal help:

| Deprecated command                      | Replacement                          |
| --------------------------------------- | ------------------------------------ |
| `memledger` executable                  | `memoryledger`                       |
| `render`                                | `build`                              |
| `agents render`                         | `build`                              |
| `agents export`                         | `export`                             |
| `templates list/show/apply/sync/remove` | `template` with the same subcommand  |
| `memory edit`                           | `memory update`                      |
| `memory status`                         | `memory set-status`                  |
| `review archive`                        | `memory archive`                     |
| `storage verify`                        | `storage validate`                   |
| `memory versions`                       | Git history / `memory show`          |
| `memory diff`                           | Git diff                             |
| `migrate storage-v2`                    | `migrate plan/apply storage-v2`      |
| `migrate linked-docs-dir`               | `migrate plan/apply linked-docs-dir` |
| `storage migrate`                       | `migrate plan/apply storage-layout`  |
| `storage recover`                       | `migrate recover storage-layout`     |
| `storage cleanup-legacy`                | `migrate cleanup storage-layout`     |

Release records are the source for deprecation release dates; no removal date is
promised here.
