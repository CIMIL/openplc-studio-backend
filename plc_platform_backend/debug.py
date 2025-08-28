import uvicorn

from plc_platform_backend.commons.configuration import get_configuration
from plc_platform_backend.main import app

if __name__ == "__main__":
    get_configuration().validate()

    uvicorn.run("debug:app", host="0.0.0.0", port=8000, reload="true")
