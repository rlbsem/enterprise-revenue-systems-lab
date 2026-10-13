# Publish after owner approval

The application has a static build in `dist/`. It contains only HTML, CSS, JavaScript and recorded synthetic evidence. It requires no secrets, Python service, PostgreSQL database or live model endpoint.

After reviewing and approving the pull request, the owner may authorize merging and enabling GitHub Pages. Until then, main contains only the bootstrap README and no deployment is enabled. An approved Pages setup should publish only `dist/`, use the repository's environment protections and keep all local execution APIs outside the deployment.

Use `python scripts/build.py` to prepare the static files and `python scripts/check_repository.py` to check the underlying evidence. Test the final public URL after deployment. A successful local build is not proof that a hosted deployment or GitHub workflow has succeeded.
