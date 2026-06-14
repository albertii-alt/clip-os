from database import supabase


def upload_file(local_path: str, storage_path: str) -> str:
    """
    Uploads a local file to Supabase Storage.
    Returns the public URL.
    """
    with open(local_path, "rb") as f:
        supabase.storage.from_("clipos-assets").upload(storage_path, f)

    return supabase.storage.from_("clipos-assets").get_public_url(storage_path)


def download_file(storage_path: str, local_path: str):
    """
    Downloads a file from Supabase Storage to a local path.
    """
    file_bytes = supabase.storage.from_("clipos-assets").download(storage_path)
    with open(local_path, "wb") as f:
        f.write(file_bytes)


def delete_file(storage_path: str):
    """
    Deletes a file from Supabase Storage.
    """
    supabase.storage.from_("clipos-assets").remove([storage_path])