import os

import uvicorn

from plc_platform_backend.commons.configuration import get_configuration

if __name__ == "__main__":
    get_configuration().validate_configuration()

    uvicorn.run(
        "plc_platform_backend.main:app",
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=8000,
        reload=True,
    )
