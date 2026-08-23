import { Module } from '@nestjs/common';

import { DatabaseModule } from '../datasources/database.module';

import { TiendaRepository } from './repositories/tienda.repository';
import { repositoryProviders } from './repositories/repository.providers';

@Module({
  imports: [DatabaseModule],

  providers: [
    ...repositoryProviders,
    TiendaRepository,
  ],

  exports: [
    TiendaRepository,
  ],
})
export class IdentificacionModule {}