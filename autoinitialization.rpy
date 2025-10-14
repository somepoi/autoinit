init -1500 python:
    import time
    import builtins
    import os

    class autoInitialization_autoinit:
        """
        Класс для автоматической инициализации ресурсов мода (изображения, спрайты, аудио, шрифты).
        Сканирует структуру папок, инициализирует ресурсы мода.
        """

        def __init__(self, modID, modPostfix="", write_into_file=False, initialize_images=True, initialize_sprites=True, initialize_audio=True, initialize_fonts=True):
            """
            :param modID: str
                имя корневой папки мода (обязательно)
            :param modPostfix: str, optional, :default value: ""
                постфикс к именам ресурсов (опционально)
            :param write_into_file: boolean, optional, :default value: False
                если True — вместо немедленной инициализации записывает ресурсы мода
                в файл `autoinit_assets.rpy`; затем потребуется перезагрузка БЛ.
                если False — ресурсы мода инициализируются сразу при загрузке БЛ.
            :param initialize_images: boolean, optional, :default value: True
                включить обработку обычных изображений (по умолчанию True)
            :param initialize_sprites: boolean, optional, :default value: True
                включить обработку спрайтов (по умолчанию True)
            :param initialize_audio: boolean, optional, :default value: True
                включить обработку аудио (по умолчанию True)
            :param initialize_fonts: boolean, optional, :default value: True
                включить обработку шрифтов (по умолчанию True)
            """

            self.modID = modID
            self.modPostfix = ("_" + modPostfix if modPostfix else "")
            
            self.EXTENSIONS = {
                "IMAGE": ('.png', '.jpg', '.jpeg', '.webp', '.gif'),
                "AUDIO": (".wav", ".mp2", ".mp3", ".ogg", ".opus"),
                "FONT": (".ttf", ".otf")
            }
            self.NAMES = {
                "IMAGES_FOLDER": "images",
                "SPRITES_FOLDER": "sprites",
                "ASSETS": "autoinit_assets",
                "LOGGER": "Logger"
            }
            self.SPRITE_TINTS = {
                "sunset": "TintMatrix(Color(hls=(0.94, 0.82, 1.0)))",
                "night": "TintMatrix(Color(hls=(0.63, 0.78, 0.82)))"
            }

            self.write_into_file = write_into_file
            self.initialize_images = initialize_images
            self.initialize_sprites = initialize_sprites
            self.initialize_audio = initialize_audio
            self.initialize_fonts = initialize_fonts
            
            self.modFiles = self.cache_mod_files()
            self.modReadyToInitFiles = []
            self.modInitializedFiles = {
                "image": 0,
                "sprite": 0,
                "sound": 0,
                "font": 0,
                "total": 0,
            }
            
            self.modPath = self.find_mod_path()
            self.modImagesPath = self.modPath + "/" + self.NAMES["IMAGES_FOLDER"]
            self.modSpritesPath = self.modImagesPath + "/" + self.NAMES["SPRITES_FOLDER"]
            self.modAssetsPath = "game/" + self.modPath + "/" + self.NAMES["ASSETS"] + ".rpy" 
            self.modLoggerPath = self.modID + self.NAMES["LOGGER"] + ".txt"

            self.modDist = self.process_distances()

            self.check_class_name()
            self.check_duplicate()

            self.logger_create()

            self.initialize()

            self.report()

            self.record_instance()
        
        #region Работа с путями
        def get_rel_path(self, dir_path, path):
            """Получаем относительный путь от path"""
            try:
                return dir_path[len(path):].strip("/")
            except Exception as e:
                self.error("Error while trying to get rel path from {} for {}: {}".format(dir_path, path, e))

        def cache_mod_files(self):
            """Прогоняем list_files и кэшируем файлы/директории, в которых есть имя корневой папки мода"""
            try:
                renpyFiles = renpy.list_files()
                modFiles = {}
                
                for file_path in renpyFiles:
                    if self.modID in file_path:
                        dir_path = "/".join(file_path.split("/")[:-1])
                        if dir_path not in modFiles:
                            modFiles[dir_path] = []
                        modFiles[dir_path].append(file_path)
                
                return modFiles
            except Exception as e:
                self.error("Error caching RenPy and mod files: {}".format(e))

        def find_mod_path(self):
            """Находит путь до папки мода."""
            try:
                for dir_path in self.modFiles:
                    if self.modID in dir_path:
                        path_parts = dir_path.split("/")
                        if self.modID in path_parts:
                            mod_index = path_parts.index(self.modID)
                            return "/".join(path_parts[:mod_index + 1])
            except Exception as e:
                self.error("Could not find mod path for modID: {}\n{}".format(modID, e))
                return None

        def process_distances(self):
            """
            Строит названия дистанций по именам внутри sprites (для normal дистанции имя будет "", как в самом БЛ), ищет первое изображение в каждой из папок с дистанциями, получает размер изображения и добавляет в словарь

            :return: dict

            Пример возврата функции:
            {
                "far": {"far", (675, 1080)},
                "normal": {"", (900, 1080)},
                "close": {"close", (1125, 1080)},
            }
            """
            try:
                folder_names = {}
                
                for dir_path, files in self.modFiles.items():
                    if self.modSpritesPath in dir_path and dir_path != self.modSpritesPath:
                        relative_to_sprites = self.get_rel_path(dir_path, self.modSpritesPath)
                        distance_name = relative_to_sprites.split("/")[0] if "/" in relative_to_sprites else relative_to_sprites
                        if distance_name and distance_name not in folder_names:
                            for file_path in files:
                                if file_path.endswith(self.EXTENSIONS["IMAGE"]):
                                    try:
                                        image_size = renpy.image_size(file_path)
                                        folder_names[distance_name] = (distance_name if distance_name != "normal" else "", image_size)
                                        break
                                    except:
                                        continue
                
                return folder_names
            except Exception as e:
                self.error("Error while processing distances: {}".format(e))
        #endregion

        #region Проверки на дубликаты и ошибки
        def check_duplicate(self):
            """Проверяем на дублированием класса/объекта класса с таким же именем"""
            try:
                registry = getattr(store, "_autoinit_registry", None)
                if registry is None:
                    registry = {"class_name_to_class_obj": {}, "initialized_class_names": set()}
                    setattr(store, "_autoinit_registry", registry)

                class_name = self.__class__.__name__

                if class_name in registry.get("initialized_class_names", set()):
                    self.error("Instance of '{}' already exists. Rename the class (change postfix).".format(class_name))

                existing_cls = registry.get("class_name_to_class_obj", {}).get(class_name)
                if existing_cls is not None and existing_cls is not self.__class__:
                    self.error("Duplicate class name '{}' detected from another file. Rename the class postfix to include your mod folder name.".format(class_name))

                registry["class_name_to_class_obj"][class_name] = self.__class__
            except Exception as e:
                self.error("Duplicate check failed: {}".format(e))

        def check_class_name(self):
            if not(self.__class__.__name__.endswith(self.modID) or self.__class__.__name__.startswith(self.modID)):
                self.error("The auto-initialization class name ({}) must be unique and contain the mod root folder name".format(self.__class__.__name__))

        def record_instance(self):
            """Помечаем успешное создание объекта класса, чтобы запретить повторные инстансы того же имени"""
            try:
                registry = getattr(store, "_autoinit_registry", None)
                if registry is not None:
                    registry.setdefault("initialized_class_names", set()).add(self.__class__.__name__)
            except Exception as e:
                self.error("Failed to record instance creation: {}".format(e))
        #endregion

        #region Логгер
        def logger_create(self):
            if renpy.windows:
                try:
                    with builtins.open(self.modLoggerPath, "w+") as logger:
                        logger.write(self.modID.upper() + " AUTOINITIALIZATION\n")
                except Exception as e:
                    self.error("Error while trying to create logger: {}".format(e))
        
        def logger_write(self, txt):
            if renpy.windows:
                try:
                    with builtins.open(self.modLoggerPath, "a+") as logger:
                        logger.write(str(txt) + "\n")
                except Exception as e:
                    self.error("Error while trying to write into logger: {}".format(e))
        #endregion

        def error(self, txt):
            """Вызываем трейсбек с названием мода и уведомлении о ошибке с автоинитом"""
            renpy.error(self.modID.upper() + " AUTOINITIALIZATION ERROR: {}".format(txt))

        def timer(func):
            """Таймер для замера скоростки отработки функций"""
            def wrapper(self, *args, **kwargs):
                start = time.time()
                result = func(self, *args, **kwargs)
                end = time.time()
                self.logger_write("{} took {:.4f} seconds".format(func.__name__, end - start))
                return result
            return wrapper
        
        def report(self):
            self.logger_write("TOTAL: {total}\nIMAGES: {images}\nSPRITES: {sprites}\nAUDIO: {audio}\nFONTS: {fonts}".format(total=self.modInitializedFiles["total"], images=self.modInitializedFiles["image"], sprites=self.modInitializedFiles["sprite"], audio=self.modInitializedFiles["sound"], fonts=self.modInitializedFiles["font"]))

        def _get_sprite_parts(self, sprite_dir, who):
            """Извлекает части спрайта из папки, если не находим тело как часть спрайта - ставим заглушку."""
            parts = {
                'body': None,
                'clothes': [],
                'emo': [],
                'acc': []
            }
            
            for dir_path, files in self.modFiles.items():
                if dir_path.startswith(sprite_dir):
                    relative_path = self.get_rel_path(dir_path, sprite_dir)
                    
                    if not relative_path:  # Корневая папка спрайта, если не нашли clothes/emo/acc и другие папки
                        for file_path in files:
                            if 'body' in os.path.basename(file_path):
                                parts['body'] = '"{}"'.format(file_path)
                                break
                    elif relative_path == 'clothes':
                        for file_path in files:
                            name_part = os.path.basename(file_path).rsplit('.', 1)[0]
                            # На случай, если имя файла включает в себя:
                            # а) префикс персонажа
                            # б) префикс персонажа и номер позы
                            if name_part.startswith(who + '_'):
                                parts_list = name_part.split('_')
                                if len(parts_list) > 2 and parts_list[1].isdigit():
                                    clothes_name = '_'.join(parts_list[2:])
                                else:
                                    clothes_name = '_'.join(parts_list[1:])
                            else:
                                clothes_name = name_part
                            parts['clothes'].append((clothes_name, file_path))
                    elif relative_path == 'emo':
                        for file_path in files:
                            name_part = os.path.basename(file_path).rsplit('.', 1)[0]
                            if name_part.startswith(who + '_'):
                                parts_list = name_part.split('_')
                                if len(parts_list) > 2 and parts_list[1].isdigit():
                                    emo_name = '_'.join(parts_list[2:])
                                else:
                                    emo_name = '_'.join(parts_list[1:])
                            else:
                                emo_name = name_part
                            parts['emo'].append((emo_name, file_path))
                    elif relative_path == 'acc':
                        for file_path in files:
                            name_part = os.path.basename(file_path).rsplit('.', 1)[0]
                            if name_part.startswith(who + '_'):
                                parts_list = name_part.split('_')
                                if len(parts_list) > 2 and parts_list[1].isdigit():
                                    acc_name = '_'.join(parts_list[2:])
                                else:
                                    acc_name = '_'.join(parts_list[1:])
                            else:
                                acc_name = name_part
                            parts['acc'].append((acc_name, file_path))
            
            if not parts['body']:
                parts['body'] = 'im.Alpha("images/misc/soviet_games.png", 0.0)'
            
            return parts

        def build_sprite(self, composite_size, body_expr, extra_layer_paths):
            """
            Собирает big-ass строчку для объявления спрайта, учитывает тинты, дистанции, и вариации спрайта.
            """
            try:
                layers_parts = ["(0, 0), {}".format(body_expr)]
                for layer_path in extra_layer_paths:
                    layers_parts.append('(0, 0), "{}"'.format(layer_path))
                layers_joined = ",\n                                            ".join(layers_parts)

                sprite_tints = ""
                for tint_name, tint in self.SPRITE_TINTS.items():
                    sprite_tints += """
                    "persistent.sprite_time=='{tint_name}'",
                    Transform(Composite({size},
                                                {layers}),
                                    matrixcolor={tint}
                                ),
                    """.format(tint_name=tint_name, tint=tint, size=composite_size, layers=layers_joined)
                sprite = """
                    ConditionSwitch(
                        {tints}
                        True,
                        Composite({size},
                                    {layers})
                    )
                    """.format(tints=sprite_tints, size=composite_size, layers=layers_joined)
                return sprite
            except Exception as e:
                return self.error("Failed to build {} sprite: {}".format(body_expr, e))

        def count_file(self, type, file_name, file):
            """
            Добавляет название файла, сам файл и его тип в лист modFiles.

            :param type: str
                тип файла
            :param file_name: srt
                имя файла
            :param file: str
                путь до файла
            """
            self.modReadyToInitFiles.append([type, file_name, file])

        #region обработка файлов
        @timer
        def process_audio(self):
            """
            Обрабатывает аудио. Поддерживает расширения (".wav", ".mp2", ".mp3", ".ogg", ".opus")

            Имя аудио для вызова будет в формате:
            [имя][_постфикс]

            Пример:
            newmusic_mymod
            """
            for dir_path, files in self.modFiles.items():
                for file_path in files:
                    if any(file_path.endswith(ext) for ext in self.EXTENSIONS["AUDIO"]):
                        file_name = os.path.basename(file_path).rsplit('.', 1)[0] + self.modPostfix
                        self.count_file("sound", file_name, file_path)

        @timer
        def process_fonts(self):
            """
            Обрабатывает шрифты. Поддерживает расширения (".ttf", ".otf")

            Имя шрифта для вызова будет в формате:
            [имя][_постфикс]

            Пример:
            newfont_mymod
            """
            for dir_path, files in self.modFiles.items():
                for file_path in files:
                    if any(file_path.endswith(ext) for ext in self.EXTENSIONS["FONT"]):
                        file_name = os.path.basename(file_path).rsplit('.', 1)[0] + self.modPostfix
                        self.count_file("font", file_name, file_path)

        @timer
        def process_images(self):
            """
            Обрабатывает изображения. Поддерживает изображения в подпапках.

            Имя изображения для вызова будет в формате:
            [папка] [подпапка] [имя][_постфикс]

            Пример:
            bg background_mymod
            bg subfolder background_mymod
            bg subfolder subsubfolder background_mymod
            """
            
            for dir_path, files in self.modFiles.items():
                if "/" + self.NAMES["SPRITES_FOLDER"] in dir_path:
                    continue
                    
                if self.modImagesPath in dir_path:
                    for file_path in files:
                        if any(file_path.endswith(ext) for ext in self.EXTENSIONS["IMAGE"]):
                            rel_to_images = self.get_rel_path(dir_path, self.modImagesPath)
                            file_name = os.path.basename(file_path).rsplit('.', 1)[0]
                            
                            if rel_to_images:
                                # Создаём имя из структуры папок
                                folder_parts = rel_to_images.split("/")
                                image_name = " ".join(folder_parts + [file_name]) + self.modPostfix
                            else:
                                image_name = file_name + self.modPostfix
                            
                            self.count_file("image", image_name, file_path)

        def process_sprite_clothes_emo_acc(self, emo_l, clothes_l, acc_l, who, file_body, dist):
            """Обрабатывает спрайт [тело] [эмоция] [одежда] [аксессуар]"""
            for emotion in emo_l:
                for clothes in clothes_l:
                    for acc in acc_l:
                        file_name = who + self.modPostfix + ' ' + emotion[0] + ' ' + clothes[0] + ' ' + acc[0] + ' ' + self.modDist[dist][0]
                        file = self.build_sprite(self.modDist[dist][1], file_body, [clothes[1], emotion[1], acc[1]])
                        self.count_file("sprite", file_name, file)

            self.process_sprite_clothes_emo(emo_l, clothes_l, who, file_body, dist)
            self.process_sprite_clothes_acc(clothes_l, acc_l, who, file_body, dist)
            self.process_sprite_emo_acc(emo_l, acc_l,  who, file_body, dist)
            self.process_sprite_emo(emo_l, who, file_body, dist)
            self.process_sprite_acc(acc_l, who, file_body, dist)
            self.process_sprite_clothes(clothes_l, who, file_body, dist)

        def process_sprite_clothes_emo(self, emo_l, clothes_l, who, file_body, dist):
            """Обрабатывает спрайт [тело] [эмоция] [одежда]"""
            for clothes in clothes_l:
                for emotion in emo_l:
                    file_name = who + self.modPostfix + ' ' + emotion[0] + ' ' + clothes[0] + ' ' + self.modDist[dist][0]
                    file = self.build_sprite(self.modDist[dist][1], file_body, [clothes[1], emotion[1]])
                    self.count_file("sprite", file_name, file)
            self.process_sprite_clothes(clothes_l, who, file_body, dist)
            self.process_sprite_emo(emo_l, who, file_body, dist)

        def process_sprite_clothes_acc(self, clothes_l, acc_l, who, file_body, dist):
            """Обрабатывает спрайт [тело] [одежда] [аксессуар]"""
            for clothes in clothes_l:
                for acc in acc_l:
                    file_name = who + self.modPostfix + ' ' + clothes[0] + ' ' + acc[0] + ' ' + self.modDist[dist][0]
                    file = self.build_sprite(self.modDist[dist][1], file_body, [clothes[1], acc[1]])
                    self.count_file("sprite", file_name, file)
            self.process_sprite_clothes(clothes_l, who, file_body, dist)
            self.process_sprite_acc(acc_l, who, file_body, dist)

        def process_sprite_emo_acc(self, emo_l, acc_l, who, file_body, dist):
            """Обрабатывает спрайт [тело] [эмоция] [аксессуар]"""
            for emotion in emo_l:
                for acc in acc_l:
                    file_name = who + self.modPostfix + ' ' + emotion[0] + ' ' + acc[0] + ' ' + self.modDist[dist][0]
                    file = self.build_sprite(self.modDist[dist][1], file_body, [emotion[1], acc[1]])
                    self.count_file("sprite", file_name, file)
            self.process_sprite_emo(emo_l, who, file_body, dist)
            self.process_sprite_acc(acc_l, who, file_body, dist)

        def process_sprite_clothes(self, clothes_l, who, file_body, dist):
            """Обрабатывает спрайт [тело] [одежда]"""
            for clothes in clothes_l:
                file_name = who + self.modPostfix + ' ' + clothes[0] + ' ' + self.modDist[dist][0]
                file = self.build_sprite(self.modDist[dist][1], file_body, [clothes[1]])
                self.count_file("sprite", file_name, file)

        def process_sprite_acc(self, acc_l, who, file_body, dist):
            """Обрабатывает спрайт [тело] [аксессуар]"""
            for acc in acc_l:
                file_name = who + self.modPostfix + ' ' + acc[0] + ' ' + self.modDist[dist][0]
                file = self.build_sprite(self.modDist[dist][1], file_body, [acc[1]])
                self.count_file("sprite", file_name, file)

        def process_sprite_emo(self, emo_l, who, file_body, dist):
            """Обрабатывает спрайт [тело] [эмоция]"""
            for emotion in emo_l:
                file_name = who + self.modPostfix + ' ' + emotion[0] + ' ' + self.modDist[dist][0]
                file = self.build_sprite(self.modDist[dist][1], file_body, [emotion[1]])
                self.count_file("sprite", file_name, file)

        def process_sprite(self, who, file_body, dist):
            """Обрабатывает спрайт [тело]"""
            file_name = "{}{} {}".format(who, self.modPostfix, self.modDist[dist][0])
            file = self.build_sprite(self.modDist[dist][1], file_body, [])
            self.count_file("sprite", file_name, file)

        @timer
        def process_sprites(self):
            """Обрабатывает спрайты и все их комбинации

            Имя спрайта для вызова будет в формате:
            [название спрайта][_постфикс]
            [название спрайта][_постфикс] [эмоция]
            [название спрайта][_постфикс] [эмоция] [одежда]
            [название спрайта][_постфикс] [эмоция] [одежда] [аксессуар]
            и любые другие комбинации.

            Пример:
            dv_mymod
            dv_mymod normal
            dv_mymod normal sport
            dv_mymod normal sport jewelry
            """
            processed_sprites = set()
            
            # Ищем все уникальные (sic!) спрайты в кэше
            for dir_path in self.modFiles.keys():
                if self.modSpritesPath in dir_path:
                    # Извлекаем путь спрайта: sprites/distance/character/number
                    relative_path = self.get_rel_path(dir_path, self.modSpritesPath)
                    path_parts = relative_path.split("/")
                    
                    if len(path_parts) >= 3:  # distance/character/number. Колхозненько, но работает
                        dist, who, numb = path_parts[0], path_parts[1], path_parts[2]
                        sprite_key = (dist, who, numb)
                        
                        if sprite_key not in processed_sprites and dist in self.modDist:
                            processed_sprites.add(sprite_key)
                            sprite_dir = "{}/{}/{}/{}".format(self.modSpritesPath, dist, who, numb)
                            
                            parts = self._get_sprite_parts(sprite_dir, who)
                            
                            # Обрабатываем все комбинации
                            self.process_sprite(who, parts['body'], dist)
                            
                            if parts['clothes'] and parts['emo'] and parts['acc']:
                                self.process_sprite_clothes_emo_acc(parts['emo'], parts['clothes'], parts['acc'], who, parts['body'], dist)
                            elif parts['clothes'] and parts['emo']:
                                self.process_sprite_clothes_emo(parts['emo'], parts['clothes'], who, parts['body'], dist)
                            elif parts['clothes'] and parts['acc']:
                                self.process_sprite_clothes_acc(parts['clothes'], parts['acc'], who, parts['body'], dist)
                            elif parts['emo'] and parts['acc']:
                                self.process_sprite_emo_acc(parts['emo'], parts['acc'], who, parts['body'], dist)
                            elif parts['clothes']:
                                self.process_sprite_clothes(parts['clothes'], who, parts['body'], dist)
                            elif parts['acc']:
                                self.process_sprite_acc(parts['acc'], who, parts['body'], dist)
                            elif parts['emo']:
                                self.process_sprite_emo(parts['emo'], who, parts['body'], dist)

        def process_files(self):
            """
            Обрабатывает файлы мода.

            Если write_into_file равно True, вместо инициализации записывает ресурсы мода в отдельный файл. Для дальнейшей инициализации ресурсов мода из файла необходимо перезагрузить БЛ.
            """
            if self.write_into_file:
                with builtins.open(self.modAssetsPath, "w") as log_file:
                    log_file.write("init -1499:\n    ")
                    for type, file_name, file in self.modReadyToInitFiles:
                        self.modInitializedFiles[type] += 1
                        self.modInitializedFiles["total"] += 1
                        if type == "sound":
                            log_file.write("$ %s = \"%s\"\n    " % (file_name, file))
                        elif type == "font":
                            log_file.write("$ %s = \"%s\"\n    " % (file_name, file))
                        elif type == "image":
                            log_file.write("image %s = \"%s\"\n    " % (file_name, file))
                        elif type == "sprite":
                            log_file.write("image %s = %s\n    " % (file_name, file.strip()))
            else:
                for type, file_name, file in self.modReadyToInitFiles:
                    try:
                        self.modInitializedFiles[type] += 1
                        self.modInitializedFiles["total"] += 1
                        if type == "sound":
                            setattr(store, file_name, file)
                        elif type == "font":
                            setattr(store, file_name, file)
                        elif type == "image":
                            renpy.image(file_name, file)
                        elif type == "sprite":
                            renpy.image(file_name, eval(file))
                    except Exception as e:
                        self.error("Failed to process {} '{}': {}".format(type, file_name, e))
        #endregion

        @timer
        def initialize(self):
            """
            Инициализация ресурсов мода и запись создания объекта класса, если не имеем уже созданный файл с объявлёнными ресурсами мода.
            """
            if not os.path.exists(self.modAssetsPath):
                if self.initialize_audio:
                    self.process_audio()
                if self.initialize_fonts:
                    self.process_fonts()
                if self.initialize_images:
                    self.process_images()
                if self.initialize_sprites:
                    self.process_sprites()
                self.process_files()