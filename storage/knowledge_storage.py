from abc import ABC, abstractmethod


class KnowledgeStorage(ABC):

    # ---------- Artifacts ----------

    @abstractmethod
    def create_artifact(self, artifact):
        pass

    @abstractmethod
    def get_artifact(self, artifact_id):
        pass

    @abstractmethod
    def list_artifacts(self):
        pass


    # ---------- Chunks ----------

    @abstractmethod
    def create_chunk(self, chunk):
        pass

    @abstractmethod
    def get_chunk(self, chunk_id):
        pass

    @abstractmethod
    def get_chunks_by_artifact(self, artifact_id):
        pass


    # ---------- Entities ----------

    @abstractmethod
    def create_entity(self, entity):
        pass

    @abstractmethod
    def get_entity(self, entity_id):
        pass

    @abstractmethod
    def find_entity_by_name(self, name):
        pass


    # ---------- Aliases ----------

    @abstractmethod
    def add_alias(self, alias):
        pass

    @abstractmethod
    def get_aliases(self, entity_id):
        pass


    # ---------- Mentions ----------

    @abstractmethod
    def add_mention(self, mention):
        pass

    @abstractmethod
    def get_chunks_for_entity(self, entity_id):
        pass

    @abstractmethod
    def get_entities_for_chunk(self, chunk_id):
        pass


    # ---------- Relations ----------

    @abstractmethod
    def create_relation(self, relation):
        pass

    @abstractmethod
    def get_relations(self, source_id=None):
        pass