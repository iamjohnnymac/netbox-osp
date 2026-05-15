# Screenshots

Captured from the live demo at <http://192.168.1.137:8000/>.

Drop the four expected files in this directory and they will surface
on the main README + mkdocs docs site:

| Filename | URL |
|---|---|
| `network_map.png` | `/plugins/osp/map/` |
| `mtp_harness_deploy.png` | `/plugins/osp/trunks/deploy-harness/` |
| `core_tracer.png` | `/plugins/osp/strands/<id>/trace/` |
| `fibre_link_loss_budget.png` | `/plugins/osp/links/<id>/` |

PNG is preferred; 1600×1000 maxes out the typical reviewer's viewport
without overshooting. Optimise via `pngquant` before committing.
