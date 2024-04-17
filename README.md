# Compression
A simple compression plugin for Prism Pipeline

## Use case
The best use case for this project is compressing old version files that might exist for compatibility reasons,
For example, having 45 versions of uncompressed ASCII save files that reach 500 MB, that's 22.5GB in possibly unused files; the plugin allows for the usage to perhaps be lowered by 1/10 depending on the compression type used.

## How it works
Using Pythons zipfile and tarfiles library, the plugin allows the user to compress any asset scene.
- Right click any asset file in prism and press compress

To decompress files back to original, just either double click or right click decompress

Right clicking a task allows for bulk compressing of files

![image](https://github.com/michal212345/Compression/assets/20019071/fd362e15-1cff-4af3-be09-59dcd35b5b70)

## Plugin settings

![image](https://github.com/michal212345/Compression/assets/20019071/f845ac3a-ea66-4ede-a196-528da69d3ec8)

- Compression type changes the file type used when compressing the file (Currently, ZIP is only supported for production)
- When Zip is selected, You can change the compression method used.
- Delete old file after compression, lets you delete the old file AFTER the file is compressed and checked.
- Open compressed file after decompression, Open the file AFTER it is decompressed and checked.
