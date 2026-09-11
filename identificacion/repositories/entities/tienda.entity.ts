import {
  Column,
  CreateDateColumn,
  Entity,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';

export enum EstadoCaptacion {
  PROSPECTO_CREADO = 'prospectoCreado',
  VISITA_1_REALIZADA = 'visita1Realizada',
  DOCUMENTOS_RECIBIDOS = 'documentosRecibidos',
  VISITA_2_REALIZADA = 'visita2Realizada',
  RUT_VALIDADO = 'rutValidado',
  HABILITADO_BASICO = 'habilitadoBasico',
  HABILITADO_AVANZADO = 'habilitadoAvanzado',
}

@Entity('tiendas')
export class Tienda {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column('varchar', { length: 100 })
  codigoInterno: string;

  @Column('varchar', { length: 100 })
  nombreComercial: string;

  @Column('uuid')
  responsableId: string;
  // es user pero ahorita lo cambio
  // TODO: Todavia me faltan cosas

  @Column('varchar', { length: 100 })
  rut: string;

  @Column('varchar', { length: 255 })
  direccion: string;

  @Column('varchar', { length: 20 })
  telefono: string;

  @Column({
    type: 'enum',
    enum: EstadoCaptacion,
  })
  estadoCaptacion: EstadoCaptacion;

  // pongo esto pq sale en todas las entities
  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}